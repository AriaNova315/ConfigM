# ConfigM

配置管理记录自动生成工具：本机浏览器录入项目、阶段、活动、配置项和基线，生成 7 类 Word 文档，并支持 Excel 导入导出。每台电脑独立运行，数据保存在本机 SQLite 中。

Windows 离线安装见 [部署手册](docs/WINDOWS_OFFLINE_DEPLOYMENT.md)，交付内容见 [交付清单](docs/DELIVERY.md)，已完成与待完成验证见 [验证记录](docs/VALIDATION.md)。Windows 实机断网验收通过前，不应视为正式放行版本。

## Mac 本机运行

推荐常规 CPython 3.14，使用独立虚拟环境。现有已安装依赖的环境可继续使用，不需要重建或迁移当前数据库。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

已有本项目 `venv` 时，可继续运行 `venv/bin/python run.py`。`python3 run.py` 在相应解释器已装好依赖时仍可用。Windows 锁文件用于 Windows 交付，Mac 安装使用 `requirements.txt`。上述首次安装命令需要网络；已安装依赖后，日常运行不需要互联网。

打开 `http://127.0.0.1:8000/`，Ctrl+C 停止。默认不监听局域网、不热重载；开发者若需要重载，可在项目根目录显式执行 `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`。不要同时启动两个实例。

## 数据与 Office

- 第一次启动自动创建空 `configm.db` 和 5 种活动类型，不导入任何样例数据；不需要外部数据库服务。
- 根目录和 `generated/` 必须可写。程序启动位置可以包含中文或空格，建议使用短的本地安装路径。
- 业务名称和文档编号保留原文。新生成的磁盘目录/文件名做 Windows 兼容处理并附加项目、阶段、文档 ID；旧导出及旧数据库路径不迁移、不删除，仍按原记录下载。
- 程序读写 Office 文件不要求安装 Word 或 Excel。查看、打印需办公软件；正式版式推荐在实际使用的 Word 中验收。含公式的输入 Excel 需先用 Excel 或已验证兼容软件重算并保存，程序只读公式缓存。
- **Excel 导入确认后会替换全部项目业务数据**，不是合并导入。导出目前只包含第一个项目，不能代替完整数据库备份。
- 服务完全停止后备份 `configm.db` 和 `generated/`。开始使用后不要随意移动安装目录，数据库中的历史输出路径为绝对路径。

## 维护与验证

```sh
venv/bin/python -m unittest discover -s tests -v
python3 scripts/build_delivery.py /tmp/ConfigM-source.zip
```

Windows 对应测试命令为 `.venv\Scripts\python.exe -m unittest discover -s tests -v`。测试只使用临时副本和合成数据，不导入项目根目录中的真实应用实例。交付脚本采用文件白名单，不包含数据库、业务 Excel、历史导出、虚拟环境或凭据，并拒绝覆盖已有交付 ZIP。

运行模板为 `templates/tpl/` 中现有 7 个 docx。不要在部署或启动时重跑 `build_templates.py`：当前运行模板包含人工修正，维护脚本不保证重现所有修正。术语“配置项”对应代码 `Product`。
