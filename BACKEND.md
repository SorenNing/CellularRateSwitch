# 原生后端保留与隔离

本仓库提供完整的新独立模块/卡片、加载器、路径桥、构建、打包及验收源码。原蜂窝切换后端和带 CommCenter entitlement 的 helper 并非本次从零重写；保留 `Vendor/` 原始二进制及来源哈希。不能把它称为已恢复原模块全部源码。

## 为什么保留

原定制通过原控制器 `updatedMenuItems` 取得 `CCUIMenuModuleItem`，读取 `identifier` 和 `isSelected`，调用原条目的 `performAction`。原后端拥有查询与切换逻辑，原 helper 持有系统蜂窝写权限。尚未完整证明原 helper 的 CLI 参数及私有 API ABI，因此不猜测4G/5G速率常量、不自造命令参数。

## 隔离过程

`tools/prepare_backend.py` 对原二进制两切片执行可复查补丁：

1. 原 `CCCellularRate` 类名族等长改为 `NNCellularRate`，避免与仍装着的 CC18 同名 Objective-C 类或其 hook 冲突。
2. 增加依赖 `@loader_path/RateSpawnBridge.dylib`。
3. 只将该后端的 `_posix_spawn` 导入改名并重绑定到私有 `_ning__spawn`：arm64 修改原 lazy-bind 操作码中的库序号，arm64e 修改 chained import 的库序号，并同步 nlist 库序号。保留其他导入、原函数代码及原生 item handler。
4. 构建时重新签名被修改的后端，不修改 CPU subtype 或 chained pointer 格式。
5. 私有桥通过自身加载路径定位同目录 `NingCellularRateTool`；原 argv（含 argv[0]）、attributes、actions、environment 不改，只重定位实际执行路径。真实 `posix_spawn` 从 libSystem 显式解析，不 hook 全进程、不修改 SpringBoard 的其他调用者。
6. `Vendor/CCCellularRateTool` 保持原件逐字节不变。首次 CI 的 macOS 严格校验报告其 arm64e 切片「code object is not signed at all」，因此交付副本使用原始 entitlements 重新生成标准 ad-hoc XML/DER 签名。禁止改业务代码、速率值或权限。`helper_invariants.py` 比较两架构全部文件支撑区段、动态依赖与完整 entitlement 字典，任何非签名语义变化都会拒绝。

后端、桥、helper 都放在本模块私有的嵌套 bundle 里，不覆盖 CC18 文件或 `/usr/local/bin/CCCellularRateTool`，不要求原 CC18 继续安装。

## 验证边界

静态重定位校验、代码段逐字节比对、双架构语法、CI 链接/签名、终包逐页代码哈希均能验证构件结构，不能替代 iOS 真机 dyld 加载、RootHide 运行期签名处理、进程派生权限、真实蜂窝切换或与 CC18 的 UI 展示共存测试。

尚未真机测试。安装后需在控制中心添加独立模块。若设备显示后端载入错误或切换未确认，应保留错误/日志排查，不把即时返回值当成功，也不要反复自动切换。
