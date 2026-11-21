# 构建与验证状态 · 2026-11-21

## 已完成

- 独立控制中心入口、原卡片式 4G/5G 选项、BOOL ABI 校验、原生状态回读与会话失效保护。
- 原后端私有类名/导入隔离，不依赖已安装的 CC18，不覆盖原 helper。
- 本机 arm64/arm64e 语法检查零诊断；生产回读策略 9042 项主机测试通过，不等于 iOS 运行测试。
- 后端两架构全部指令区段与原二进制相同；私有路径桥主机替身测试确认 argv[0]、后续参数及环境保留。
- GitHub Actions 仅手动触发；源码提交不会自动构建。

## 两次已授权构建

1. run `44874682609`，attempt 1，源码 `7fa010702078cd244c3a165664598c2c56fa7030`：原 helper arm64e 切片未通过 macOS 严格签名校验。已改用完整原始 entitlements 重签交付副本；保留 Vendor 原始文件，并逐区段/依赖/entitlement 字典核对不变。
2. run `44875136215`，attempt 1，源码 `c62705a4bc62e74c669ae82654945125073d2c5d`：两架构编译、helper 重签、全部程序构建阶段签名检查、deb 结构/代码页/架构及 helper 不变量检查通过。但终包解包后，主模块出现 `code has no resources but signature indicates they must be present`，因此整个任务失败，未上传构建产物，不能交付。

第二次失败产物仅日志中出现大小/哈希，不在本地；不能将日志当成已下载安装包。

## 当前修复（尚待一次新的授权构建验证）

- 所有主模块资源、Info.plist、内层后端先装入最终外层 bundle，最后签署整个外层 bundle，保留其 `_CodeSignature/CodeResources`。
- 打包器直接封装已签名完整目录，不在签名后重新拼接模块文件。
- 资源封装验收核对 CodeDirectory 中绑定的 Info 和 CodeResources 特殊槽，以及普通资源哈希；缺失封装直接失败。
- 终包在 macOS 解包后对内外 bundle 分别 `codesign --verify --strict --deep`。
- 资源封装检查的合成正例、篡改 Info/封装/资源的三个反例、缺封装反例通过；这些单元测试不是 Apple 原生签名成功的证明。

没有真机安装、注入、注销或蜂窝切换测试，没有上软件源。上一轮许可已使用；后续构建仍需新的单次授权。
