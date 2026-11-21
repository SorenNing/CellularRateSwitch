#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
mkdir -p build dist
python3 tools/prepare_backend.py
python3 - <<'PY'
from pathlib import Path
import hashlib
p=Path('Vendor/CCCellularRateTool')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='43cbf8c9c7da7897b13691aa434f44fb4a494ea32d430d54de62da4f46f11fb4'
PY
for ARCH in arm64 arm64e; do
  BUNDLE="build/${ARCH}/payload/Library/ControlCenter/Bundles/NingCellularRate.bundle"
  BACKEND="$BUNDLE/RateBackend.bundle"
  cp Resources/Info.plist "$BUNDLE/Info.plist"
  cp Resources/CCCellularRate@3x.png "$BUNDLE/CCCellularRate@3x.png"
  cp Resources/SettingsIcon@3x.png "$BUNDLE/SettingsIcon@3x.png"
  xcrun --sdk iphoneos clang -O2 -Wall -Wextra -Werror -fvisibility=hidden \
    -isysroot "$SDK" -target "${ARCH}-apple-ios16.0" -dynamiclib \
    -Wl,-fixup_chains -Wl,-install_name,@loader_path/RateSpawnBridge.dylib \
    src/RateSpawnBridge.c -o "$BACKEND/RateSpawnBridge.dylib"
  xcrun --sdk iphoneos clang -fobjc-arc -fblocks -O2 -Wall -Wextra \
    -Werror=implicit-function-declaration -Werror=objc-method-access -Werror=incomplete-implementation \
    -isysroot "$SDK" -target "${ARCH}-apple-ios16.0" -dynamiclib -Isrc -Ftools/linker \
    -framework Foundation -framework UIKit -framework CoreGraphics -framework QuartzCore \
    -Wl,-needed_framework,ControlCenterUIKit -Wl,-fixup_chains \
    -Wl,-install_name,@loader_path/NingCellularRate \
    src/NINGCRModule.m src/NINGCRBackend.m -o "$BUNDLE/NingCellularRate"
  cp Vendor/CCCellularRateTool "$BACKEND/NingCellularRateTool"
  cp Resources/CCCellularRate@3x.png "$BACKEND/NNCellularRate@3x.png"
  cp Resources/SettingsIcon@3x.png "$BACKEND/SettingsIcon@3x.png"
  # Renew the helper signature with precisely the original XML/DER entitlements.
  # Original vendor bytes remain archived; verify every file-backed section below.
  xcrun codesign --force --sign - --timestamp=none --generate-entitlement-der \
    --entitlements Vendor/helper-entitlements.plist "$BACKEND/NingCellularRateTool"
  xcrun codesign --force --sign - --timestamp=none "$BACKEND/RateSpawnBridge.dylib"
  xcrun codesign --force --sign - --timestamp=none "$BACKEND"
  # Seal the complete outer bundle, including Info.plist and nested resources.
  # Never sign a detached executable and then place it inside an unsealed bundle.
  xcrun codesign --force --sign - --timestamp=none "$BUNDLE"
  xcrun codesign --verify --strict --all-architectures "$BACKEND/RateSpawnBridge.dylib"
  xcrun codesign --verify --strict --all-architectures "$BACKEND/RateBackend"
  xcrun codesign --verify --strict --all-architectures "$BACKEND/NingCellularRateTool"
  xcrun codesign --verify --strict --all-architectures "$BUNDLE/NingCellularRate"
  xcrun codesign --verify --strict --deep "$BUNDLE"
  test -s "$BUNDLE/_CodeSignature/CodeResources"
done
cp build/backend-relocation.json dist/
python3 tools/package.py
python3 tools/verify.py
python3 tools/verify_macos.py
