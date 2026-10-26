
## 项目上下文（每次新会话必读）

### 这是什么项目
ConfigM：配置管理记录自动生成系统。CM专员录入项目信息，系统自动生成7种Word格式配置管理文档。
技术栈：Python + FastAPI + SQLite + Alpine.js + docxtpl

### 关键文档路径
- **设计文档（APPROVED）**：`~/.gstack/projects/ConfigM/gaoyiman-unknown-design-20260422-105530.md`
- **工程实现规范（DDL + API + 字段映射）**：`~/.gstack/projects/ConfigM/gaoyiman-unknown-eng-review-20260525-155328.md`
- **模板字段确认（两轮）**：
  - `/Users/gaoyiman/Desktop/Code/5000B/ConfigM/模版确认事项说明.md`
  - `/Users/gaoyiman/Desktop/Code/5000B/ConfigM/模版字段二轮说明.md`
- **原始Word模板**：`templates/`（7个文件）；运行模板为 `templates/tpl/`（7个文件）
- **当前部署说明**：`README.md`、`docs/WINDOWS_OFFLINE_DEPLOYMENT.md`、`docs/DELIVERY.md`
- **当前验证状态**：`docs/VALIDATION.md`；外部历史设计文档只作背景，部署无需这些开发机路径。

### 当前阶段（更新于 2026-10-26）
**已完成：**
- ✅ docxtpl 动态增行 POC 验证通过
- ✅ 7个Word模板字段两轮确认完毕
- ✅ 数据库DDL + API接口 + 字段映射表输出完成
- ✅ 7个 docxtpl 占位符模板生成完毕（`build_templates.py` → `templates/tpl/*_tpl.docx`，全部渲染验证通过）
- ✅ 项目骨架搭建完成（FastAPI + SQLite + Alpine.js）
- ✅ 全部后端模块实现（projects / phases / activities / products / baselines / documents / activity_types）
- ✅ 流水号预分配引擎（`app/services/sequence.py`）
- ✅ 7种文档生成器（`app/services/generator.py`）
- ✅ Alpine.js 单页前端（5个Tab：项目、阶段、活动、配置项&基线、生成文档）
- ✅ 文档生成验证：7类文档已逐一生成并人工核对
- ✅ 模板占位符修复（ZDPX前缀、代码+版本空格、基线标识、审核项"不适用"等）

**关键文件：**
- `build_templates.py`：占位符注入维护脚本；当前运行模板有人工修正，部署和启动不得重跑覆盖
- `templates/tpl/`：7个 `*_tpl.docx` 模板文件（已修正占位符）
- `app/services/generator.py`：文档生成逻辑，含 AUDIT_RULES 审核规则表
- `app/services/sequence.py`：流水号引擎，格式 `ZDPX-{code}/{version}-配置管理-{label}-{seq:03d}`
- `app/static/templates/index.html`：前端单页应用
- `run.py`：跨平台启动入口，推荐虚拟环境 Python；单机 127.0.0.1:8000、单进程、关闭 reload

**已修复的模板问题（直接修改 tpl/*.docx XML）：**
- 模版01/02：配置项标识和版本之间加空格（`{{ item.code }} {{ item.version }}`）
- 模版03：基线标识改为直接使用 `{{ baseline.code }}`（不再拼接 ZDPX 前缀）
- 模版03：发布说明中 XXX 改为 `{% for it in items %}{{ it.name }} {{ it.version }}{% endfor %}`
- 模版07：报告时间范围去掉多余的 `{{ activity_date }}`，只保留 `{{ phase.start_date }}`
- 所有模板：`ZDPX-{{ project.code }}` → `ZDPX{{ project.code }}`（项目代号表格内不带连字符）

**已知规则（新会话必知）：**
- Mac 可继续用已有 `venv/bin/python run.py`；系统 Python 已装依赖时 `python3 run.py` 仍可用。Windows 用 `start.cmd` 和 `.venv`。
- 常规 CPython 3.14；Mac 安装用 `requirements.txt`，Windows 离线安装用 `requirements-win.lock.txt`。
- 新输出路径由 `app/core/output_paths.py` 处理：可读名称附项目/阶段/文档 ID，Windows 安全字符和保守长度预算。原有文件/业务字段不改名、不迁移。
- 首页 Alpine.js 随代码本地交付；默认 docs/redoc 关闭。Word/Excel 不是后台服务依赖，公式重算与查看另见部署手册。
- 不启动真实应用做测试：`python -m unittest discover -s tests -v` 会创建干净临时副本并只使用合成数据。
- 产品级配置审核：`cm_manager` = `f"{proj.cm_manager}、{proj.leader}"`；阶段级只用 `proj.cm_manager`
- AUDIT_RULES：所有非"是"项均为"不适用"（不是"否"）

**术语对照（重要）：**
- 用户侧称"配置项"= 代码里的 `Product` / 数据库表 `products`，**不改数据库和后端代码**，只改前端显示文字
- "产品管理" Tab → 改为"配置项管理"
- "产品结构表" Sheet → 用户已改为"配置项清单"

**历史 Excel 导入/导出需求（已于 2026-05-29 实现）**

以下为已实现的业务规则，部署适配不改变：

*导入流程：*
1. 上传 Excel → 清空数据库 → 重新导入
2. "项目信息" Sheet → 项目基本信息
3. "项目进度计划" Sheet → 阶段（WBS整数行）+ 配置管理活动（WBS x.y.z 且父节点为"配置管理活动"）
4. "配置项清单" Sheet → 配置项（含版本列）
5. "基线组成" Sheet → 基线及关联配置项（含版本列）
6. 发布基线活动 → 用任务名称与基线名称模糊匹配（包含关系）
7. 导入完成后统一弹窗：入库活动选 checkin_reason、出库活动填 checkout_reason

*活动识别规则（任务名称关键字匹配）：*
- 含"入库" → 产品入库（需关联配置项，必填）
- 含"出库" → 出库（需关联配置项，必填）
- 含"发布" AND 含"基线" → 发布基线（关联配置项从基线组成查，不填关联列）
- 含"配置状态纪实" → 配管清单（不填关联列）
- 含"配置管理报告" → 配管报告（不填关联列）

*关联配置项格式：*
- 入库/出库活动：在"关联配置项"列用中文逗号"，"分隔多个配置项标识

*导出流程：*
- 从数据库读取所有数据，按同样 Sheet 结构写出 Excel 文件（可再次导入）

*当前交付空白输入模板：* `resources/ConfigM导入模板.xlsx`。profiles/ 是本机业务输入，不能提交或交付。

**Excel 导入/导出已实现（2026-05-29）：**
- `app/services/importer.py`：解析 + 导入 + 导出逻辑
- `app/api/routes/importer.py`：POST /api/import/parse、POST /api/import/confirm、GET /api/export
- 前端：header 加"导入 Excel"/"导出 Excel"按钮，导入后弹确认 Modal
- 依赖：`python-multipart`，现已纳入固定依赖；不再要求修改系统 Python。
- Tab"产品管理"已改为"配置项管理"

**Windows 离线交付适配（2026-10-26）：**
- ✅ 固定依赖、本地 Alpine.js、单机启动入口、start.cmd、安全输出路径和原子保存。
- ✅ 空白四 Sheet Excel 模板、交付白名单打包脚本、部署/验证文档。
- ✅ Mac 干净副本初始化、Excel 流程、七类文档和路径回归测试。
- 待验收：Windows 实机断网安装、start.cmd、真实 Word 占用与 Office 版式；状态以 docs/VALIDATION.md 为准。
- 本机 configm.db、profiles、generated 历史数据不能随包带出；导入确认会替换所有项目业务表，导出只取第一个项目，不能代替完整备份。

### 会话开始时的操作
1. 读取工程实现规范文档（上方路径）
2. 确认当前阶段是否有变化
3. 询问用户从哪里继续

### 里程碑更新规则
每完成一个任务后，自动判断是否需要更新本文件，无需用户提醒。以下情况必须更新：
- 完成一个功能模块或修复了影响后续开发的问题
- 发现并确认了新的术语对照、规则或约定
- 「下一步」列表发生变化
- 有新的关键文件路径或配置项需要记录

更新时：打✅标记已完成项，更新「下一步」列表，补充新的规则或约定。

---

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
