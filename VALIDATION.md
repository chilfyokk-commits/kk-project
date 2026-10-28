# 本次验证记录

- 环境：Linux x86_64，Python 3.12.14。
- 依赖：已在 `.venv` 中安装全部运行依赖、pytest 与 PyInstaller。
- `python -m pytest -q`：**15 passed in 3.26s**。
- 检验覆盖：描述统计均值/样本标准差、手算 Welch t 与自由度/双侧 p、配对 t、已知卡方与 ANOVA、相关系数、已知回归系数与自由度、频数、缺失处理、错误输入、CSV/XLSX/SAV/TXT 读写、单列/GB18030/带引号 CSV、Qt 编辑/事件循环、Excel/CSV/PDF 结果导出。
- 已实际启动 Qt 离屏窗口并查看中文分析结果截图。
- `bash -n scripts/build_macos.sh`：通过。
- 未执行真实 macOS 打包、DMG 装载、Gatekeeper 验证、macOS 深色模式人工检查。GitHub 上尚未触发工作流，也没有已生成的 Mac 安装包。
- 工作区未挂载有效 Git 仓库，未建立远程连接、推送或创建发布。源码位于 `/workspace/kk-project`。
