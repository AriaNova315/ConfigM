# Windows 单机离线部署

## 环境与职责

推荐 Windows 11 x64、常规 CPython 3.14 x64、已安装 Edge/Chrome、本地可写短目录。候选解释器为 3.14.10；准备与目标机统一补丁版本。当前 Windows 验证状态见 [VALIDATION.md](VALIDATION.md)，未通过实机验收前不宣称正式可部署。ARM64、32 位、free-threaded Python 不在本交付基线内。

实施方提供源码、本地静态资源、14 个模板、空白 Excel 模板、固定依赖和本手册。部署人员在联网 Windows 下载完整 Python 安装程序、准备 wheelhouse，带入目标机。每台电脑独立运行；不配置共享数据库、共享目录或局域网入站访问。

服务本身无需 Office、Node.js、Git、SQLite 服务或编译工具。Word 用于输出查看、打印与排版验收；Excel 用于输入编辑和公式重算。有公式的输入需先重算保存，程序不执行公式或 VBA。系统字体优先使用宋体、黑体及 Office 的回退；模板引用的 Noto Sans CJK SC 若缺失，需要在实际 Word 中验收回退版式，不能未经授权复制字体。

## 1. 联网 Windows 准备

从 [Python 3.14.10 发布页](https://www.python.org/downloads/release/python-31410/) 下载 `python-3.14.10-amd64.exe` 完整安装程序，不使用联网引导安装器、Store 或 embeddable ZIP。核对发布页 SHA-256 和数字签名。安装解释器、标准库、pip、venv；可安装 py launcher，不选择需要额外下载的调试组件。

源码包解压至 `D:\ConfigM-delivery\source`，安装器放到同级 python 目录。以下在 PowerShell 执行；盘符可替换：

```powershell
Set-Location D:\ConfigM-delivery
py -3.14 -c "import sys, struct; print(sys.version); print(struct.calcsize('P') * 8)"
py -3.14 -m venv .prepare-venv
.\.prepare-venv\Scripts\python.exe -m pip --disable-pip-version-check download --no-cache-dir --only-binary=:all: --dest .\wheelhouse -r .\source\requirements-win.lock.txt
Get-FileHash .\python\python-3.14.10-amd64.exe -Algorithm SHA256
Get-ChildItem .\wheelhouse\*.whl | Get-FileHash -Algorithm SHA256
```

确认解释器是常规 3.14.x、64 位。无 py 时使用已安装 Python.exe 的完整路径。无需升级 pip；若完整安装器配套 pip 确有问题，应先在准备机解决并固定离线包，不能现场联网修补。Windows 锁文件显式固定所有传递依赖，包括 Windows 专用 colorama；准备机必须为 Windows，以正确求值平台条件。

`--only-binary=:all:` 遇到缺少 wheel 会失败。此时将完整报错交给实施方，不能去掉该参数改装源码包。准备机与目标机使用同架构、同 Python 次版本和补丁，优先同 Windows 版本。校验记录和成功验收环境另存为 ENVIRONMENT.txt；不用开发机的 macOS venv。

## 2. 在干净 Windows 验证离线安装

使用另一目录或 Windows 虚拟机，断开外网、禁用 pip 缓存，按下一节完整安装。检查 wheelhouse 不缺传递依赖。验证成功后再将安装器、源码包、wheels、校验清单及手册带入目标机。交付脚本不会自动下载 Python 或库。

## 3. 目标机全新安装

安装完整 Python 程序。将源码 ZIP 解压至最终目录，例如当前用户的 `%LOCALAPPDATA%\ConfigM`。该目录不能带入 configm.db、profiles 或 generated 历史文件，不能覆盖现有安装。避免 Program Files、共享盘、同步盘和过长目录。

```powershell
Set-Location "$env:LOCALAPPDATA\ConfigM"
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip --disable-pip-version-check install --no-cache-dir --no-index --only-binary=:all: --find-links "D:\ConfigM-delivery\wheelhouse" -r .\requirements-win.lock.txt
.\.venv\Scripts\python.exe -m pip --disable-pip-version-check check
.\.venv\Scripts\python.exe -c "import sys, struct; print(sys.executable); print(sys.version); print(struct.calcsize('P') * 8)"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\start.cmd
```

直接调用 `.venv\Scripts\python.exe`，不需要激活环境或修改 PowerShell 执行策略。安装失败不要去掉 `--no-index`，回联网准备机补 wheelhouse 后重试。确认根目录、generated 和系统 TEMP 可写。

打开 `http://127.0.0.1:8000/`。首次启动自动建空数据库，项目列表为空、活动类型 5 个；第二次启动不增加重复种子。数据库正常初始化不需要导入 Excel。不要运行 build_templates、POC、清库或真实业务导入脚本来“完成安装”。

## 4. 日常启动和使用

双击 `start.cmd`，或执行 `.venv\Scripts\python.exe run.py`。启动脚本定位自身目录，含空格/中文路径无需自行改代码。仅监听 `127.0.0.1:8000`，单进程、关闭 reload，默认不提供 `/docs` 和 `/redoc`；业务页面和 API 正常使用，不开防火墙入站规则。

停止时在控制台 Ctrl+C；不要同时启动多个实例或用多个窗口并行操作导入确认。Alpine.js 已在本机 static/vendor 中，日常启动无 CDN、字体或包自动下载。

导入模板见 `resources/ConfigM导入模板.xlsx`，字段/WBS/关联说明见 [DELIVERY.md](DELIVERY.md)。**确认导入会替换全部项目业务数据**，不会合并。导出只包含第一个项目，不能作为多项目完整备份。

## 5. 输出、备份及故障排查

- 新输出保留可读目录名，并附 `_p项目ID`、`_s阶段ID`、`_d文档ID`。仅磁盘名称清理 Windows 禁用字符并按 UTF-16 长度缩短，Word 正文和业务编号不变。旧文件仍按数据库中的原路径下载，不自动改名或清理。
- 服务完全停止后备份 configm.db 与 generated，并确认无本应用活动连接。运行中不要直接复制数据库作为一致性备份，也不要手动删除 SQLite 伴随文件。恢复应停机、保留当前副本，再使用配套数据库与文件目录；开始使用后不随意移动安装目录。
- **端口占用**：PowerShell 执行 `Get-NetTCPConnection -LocalPort 8000`，确认是否本应用已启动。不结束不明进程；如组织要求更换端口，由维护方统一修改启动入口和说明。
- **无法保存文档**：先关闭正打开输出的 Word/WPS 等软件，再确认目录可写、磁盘空间充足。程序先写同目录临时文件，成功后替换；替换失败会返回明确错误，旧文件保留。
- **路径过长**：优先选择短的安装目录；不要以修改注册表长路径设置作为唯一解决方式。程序按保守的完整路径长度预算处理，安装根路径本身过长时会提示。
- **公式值为空或过时**：先在 Excel/经验证兼容软件中重算、保存后再上传。不要期望 openpyxl 重算，也不要以导入真实表作为安装测试。
- **模板缺失或渲染异常**：用交付 hash 清单核对 templates/tpl 的 7 个文件；不要自行重跑模板维护脚本覆盖当前模板。
- **依赖错误**：确认 start.cmd 使用本目录 .venv，并执行 pip check；不要向系统 Python 混装库。
- **Word 版式差异**：核对 Office 版本、字体和打印设置，在实际使用的软件中验收七类合成输出。

## 6. Windows 最终验收记录

记录 Windows 版本/架构、Python 完整版本和安装器 hash、pip freeze/pip check、wheelhouse hashes、浏览器/Office 版本、离线安装输出和七类文档结果。测试中文/空格安装目录、特殊名称、重名、长路径、文件被 Word 占用、重启持久化、单文档/ZIP 下载及导入导出。

使用新浏览器配置、禁用缓存并断外网，检查应用全部 Tab、确认窗口以及网络面板；应用请求只能指向 127.0.0.1。只有实际完成这些项目后，才能将 [VALIDATION.md](VALIDATION.md) 的 Windows 状态标为通过。
