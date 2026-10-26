# 部署适配验证记录

日期：2026-10-26。基线：`457aedd`。本记录描述源码交付准备，不是 Windows 正式放行声明。

## 已执行

- macOS 常规 CPython 3.14.3，使用既有 venv，没有升级本机依赖。
- `venv/bin/python -m unittest discover -s tests -v`：5 项测试通过，包括路径兼容和隔离集成流程。
- `venv/bin/python -m pip check`：No broken requirements found。
- 干净副本位于含中文、空格的临时路径，使用合成项目，覆盖空数据库首次启动、重启种子幂等、关闭 docs/redoc、本地 Alpine、Excel multipart 上传/解析/确认/导出及重新解析、七类 Word 生成和下载、ZIP 下载、修改后重启持久化。
- 路径测试覆盖禁用字符、保留名、UTF-16 长度、清理/截断后重名、路径穿越；文件替换失败保留旧文件并可重试。
- 现有数据库、profiles、generated 历史输出和 14 个原始/运行模板用 SHA-256 对照，确认未因适配或测试改写。
- 本地 Alpine 来源为固定的官方 npm 3.15.12 发布包，按 npm 元数据 SHA-512 验证 tarball，并保留上游 MIT 许可证及本地文件 SHA-256。
- Windows x64 / cp314 的 25 个 wheel（包括 colorama）下载成功。逐包读取 METADATA，并按 Windows/AMD64/CPython 3.14 平台条件和 SQLAlchemy asyncio extra 检查，全部依赖在这 25 个固定包内闭合。未在 Windows 安装。
- Chromium 访问干净交付包副本：首页和本地 Alpine.js 返回 200，初始化 API 成功，全部已观察初始化请求指向 127.0.0.1，控制台无错误；通过表单保存合成项目后进入阶段页面。没有在此步骤断开宿主机外网，真正断网验证仍在 Windows 验收项中。
- start.cmd 已核对 CRLF，内嵌 Python 环境检查在本机正常返回；Windows cmd 执行仍待实机验证。
- 交付 ZIP 内文件 hash 清单逐项核验通过，未包含数据库、profiles、generated、虚拟环境或 Actions。

## 待补充的环境验证

- Windows 11 x64、常规 CPython 3.14.10 完整安装器断网安装。
- 在目标 Windows 平台标记下准备 wheelhouse，在无缓存/无外网的干净 Windows 完整安装并 pip check。
- Windows start.cmd 双击启动、中文/空格目录、仅本机监听、真实文件占用与文件锁释放。
- Word/Excel 实际查看、分页/字体回退、打印及公式重算保存。

Mac 上针对 win_amd64/cp314 的 wheel 下载只证明指定文件可下载，不等同 Windows 的依赖标记解析、安装或运行。若没有 Windows 环境，保留本节为待验收，不能用本机测试替代。

## 复验命令

```sh
venv/bin/python -m unittest discover -s tests -v
venv/bin/python -m pip check
python3 scripts/build_delivery.py /tmp/ConfigM-source.zip
```

Windows 使用 `.venv\Scripts\python.exe` 运行同一 unittest 命令；安装准备命令见离线手册。所有 smoke 初始化只发生在临时副本，不能手动将 smoke_worker.py 指向真实安装目录。
