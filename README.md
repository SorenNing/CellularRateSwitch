# 蜂窝4/5G切换 · CellularRateSwitch

从 Ning 的 CC18 定制中独立提取的系统控制中心模块，面向 iPhone、iOS 16/17。无需安装 ControlCenter18，不修改其设置、布局或现有模块。

## 功能

- 紧凑按钮点击或长按请求系统展开；卡片标题「蜂窝4/5G切换」。
- 「切换5G」「切换4G」两行，保留原定制卡片居中布局与选中标记。
- 严格区分原生 BOOL / _Bool / 对象类型编码，修复早期误按 void 过滤选项的问题。
- 切换动作仅执行一次；不把动作即时返回值当成切换成功。每 0.2 秒回读原生设置，最多 8 秒；排他选中目标档位才确认。
- 折叠、离开控制中心或会话失效后，旧回调不再修改界面。
- 只在真实展开路径创建蜂窝后端，无启动目录预热、无全局 hook、无构造器重试。

这里的4G/5G是蜂窝最大数据速率/网络模式设置，不保证运营商实际驻留5G，也不是修改状态栏文字。当前蜂窝数据订阅按原后端选择，不新增双卡选择器。

## 构建

仅使用 GitHub Actions 的 `workflow_dispatch` 手动触发，runner 为 `macos-latest`。push 不触发构建。构建前先同步并核对 main 源码；一次请求只触发一次构建，失败不自动重试。

本工程同时产出：

- `iphoneos-arm64`：普通无根包，安装在 `var/jb/`。
- `iphoneos-arm64e`：RootHide 包，根 `Library/` 布局；原生 arm64e 编译，Mach-O subtype 必须为 `0x80000002`，不能改头冒充。

```sh
bash tools/build-macos.sh
python3 tools/check_source.py
python3 tools/verify.py
```

打包使用 Python 确定性 ar/USTAR/gzip，显式包含父目录与权限，不调用 macOS `ar`。不附带自动注销、安装或启用脚本。

## 验证边界

源码语法、状态机、Mach-O 逐页签名/架构、安装包清单校验与真机功能是不同层级。CI 通过不代表手机上的蜂窝切换、动画或稳定性已实测；需用户安装后验证。

## 图标与署名

复用原蜂窝模块资源，不设计新的图标。新独立适配署名 Ning，原蜂窝模块来源标识为 Netskao；原二进制来源、哈希与保留范围见 `Vendor/provenance.json`。不包含其他 CC18 模块、控制中心主程序或其设置页。
