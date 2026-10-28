# StatMate

免费的 macOS 中文统计分析桌面软件，使用 Python、PySide6 和真实统计库。面向大学统计课程练习，独立实现，不依赖或破解 IBM SPSS。当前版本 0.1.0。

## 已实现

- 可编辑数据视图；添加变量、添加观测；变量视图设置数值/文本、变量标签、值标签、离散缺失值、名义/有序/尺度。
- 导入 SAV、XLS、XLSX、CSV、TXT。文本自动识别分隔符，优先 UTF-8，兼容 GB18030；Excel 默认读取第一个工作表。
- 描述统计、频数、交叉表、Pearson 卡方、Welch 独立样本 t、配对 t、单因素方差分析、Pearson 相关、OLS 线性回归。
- 结果包含适用的样本量、统计量、自由度和双侧 p 值；回归包含系数、标准误、置信区间和模型拟合信息。
- 累积结果可导出 Excel、CSV、PDF；直方图可单独导出 PDF/PNG。
- 数据可导出 CSV、XLSX、SAV；SAV 保留变量设置。CSV/Excel 不保留变量元数据。
- Qt 跟随 macOS 系统明暗主题，使用原生文件窗口和 Command 快捷键（⌘O 导入、⌘S 保存、⌘R 分析）。

## 下载与安装 Mac 版

源码提交到你的 GitHub 仓库后：

1. 打开仓库 **Actions → 构建 StatMate Mac 安装包 → Run workflow**。推送到 main/master 或 v 开头的标签也会触发。
2. 等待两个 macOS 作业通过，进入该次运行页面底部 **Artifacts**。
3. Apple 芯片（M1/M2/M3/M4 等）下载 `StatMate-macOS-arm64`；Intel Mac 下载 `StatMate-macOS-x86_64`。可在“苹果菜单 → 关于本机”查看芯片。
4. 解压下载的 artifact ZIP，双击其中的 `.dmg`，将 **StatMate.app 拖到 Applications（应用程序）**。
5. 从“应用程序”双击 StatMate 启动。无须安装 Python。也可使用 artifact 内 `.app.zip`，解压后拖入应用程序。

**构建状态说明：** 本开发环境为 Linux，没有真实的原始 Git 仓库挂载、GitHub 远程地址和 macOS 工具链。本次提供源码与工作流，不声称已生成 Mac 二进制。只有 GitHub 上相应作业成功后，才会出现真实可下载的 `.app`/`.dmg`。本地 Linux 测试不能替代 macOS 运行验证。

**签名限制：** 当前采用临时（ad-hoc）签名，没有 Apple Developer ID 签名和 Apple 公证。首次运行可能被 Gatekeeper 拦截。确认下载来自你自己的可信构建后，尝试按住 Control 点按应用选择“打开”，或在“系统设置 → 隐私与安全性”中选择“仍要打开”。不同 macOS 版本操作可能有差异；受管理的 Mac 可能不允许启动。不要全局关闭 Gatekeeper。正式分发前需要配置开发者签名与公证。

GitHub 工作流使用 macos-14（arm64）与 macos-15-intel（x86_64），Python 3.12，执行测试、PyInstaller 打包、真实程序启动存活检查及 DMG 校验，然后上传安装包。当前目标为 macOS 14 及以上（Intel 建议 macOS 15）；更旧系统尚未验证，非 universal2 包。若 GitHub 调整 runner 名称，需按其支持列表更新工作流。

## 使用方式

从“文件 → 导入数据”打开课程数据。在数据视图双击编辑单元格；空白表示系统缺失。在变量视图中，值标签采用 JSON 对象，例如 `{"1":"男","2":"女"}`，缺失值采用数组，例如 `[99,999]`。变量名称目前创建后不可改名。

从“分析 → 选择统计分析”选择方法与变量。可拖动变量列表调整顺序：独立样本 t/方差分析先选数值因变量、后选分组变量；回归第一项为因变量，其余为自变量。运行后切换至结果页，“文件 → 导出分析结果”保存报告。

从“分析 → 绘制直方图”选择数值变量。分析表和图表分别导出。分析结果为当前会话快照，修改数据后请重新运行分析。

## 统计约定与当前边界

描述统计使用样本标准差（ddof=1）；频数百分比基于非缺失观测。统计分析使用配置的缺失值；多变量分析采用完整案例删除。相关分析采用所有选中变量整组删除。独立 t 使用 Welch 自由度；卡方不使用连续性校正，输出低期望频数单元格数；单因素 ANOVA 假定等方差。未提供加权、复杂抽样、事后检验、非参数分析、自动假设检验或 SPSS 语法执行。

SAV 导入读取原始编码，不把值标签替换成文本。范围缺失值按文件中已出现的值展开；后续新增该范围内值时需自行补充缺失设置。SAV 导出受格式限制（例如合法变量名及最多三个离散缺失值）；库报错会显示中文操作提示与具体原因。尚不支持保留 SAV 全部扩展属性。数据编辑与结果导出面向课程规模数据，超大文件会阻塞界面。

原生 Qt 按系统设置呈现深色模式；系统对话框和窗口按钮可能采用操作系统语言。中文图表依赖 macOS PingFang 字体。PDF 表格使用 Qt 排版，特别宽的回归表建议导出 Excel。

## 从源码运行与测试

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m statmate
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

本地生成安装包（**必须在对应架构 macOS 上运行**）：

```bash
bash scripts/build_macos.sh
```

输出位于 `dist/StatMate.app` 与 `dist/StatMate-macOS-arm64.dmg` 或 `dist/StatMate-macOS-x86_64.dmg`。构建脚本在 Linux 上会拒绝运行。

测试覆盖手算/已知值统计核对、缺失处理、CSV/TXT/XLSX/SAV 往返、GUI 单元格编辑和 XLSX/CSV/PDF 导出。XLS 通过 xlrd 导入，尚无自动化二进制样例覆盖。

## 许可

MIT，允许免费使用、修改和分发，见 LICENSE。依赖各自适用其许可；PySide6/Qt 使用 LGPL 或其商业许可条款，分发者应遵守相应要求。
