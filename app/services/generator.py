"""
docxtpl 文档生成服务。
Context 变量名以实际模板占位符为准。
"""
import json
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace
from docxtpl import DocxTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TEMPLATES_DIR, GENERATED_DIR
from app.core.output_paths import document_path, save_document
from app.models.models import (
    Activity, ActivityProduct, ActivityType, Baseline, BaselineProduct,
    DocumentRecord, Phase, Product, Project,
)

TPL_DIR = TEMPLATES_DIR   # already points to templates/tpl/
GEN_DIR = GENERATED_DIR

TPL_MAP = {
    "入库申请":       "模版01-入库申请单_tpl.docx",
    "出库申请":       "模版02-出库申请单_tpl.docx",
    "基线发布":       "模版03-基线发布单_tpl.docx",
    "配置审核_产品级": "模版04-配置审核报告（产品级）_tpl.docx",
    "配置审核_阶段级": "模版05-配置审核报告（阶段级）_tpl.docx",
    "配管清单":       "模版06-配管清单_tpl.docx",
    "配管报告":       "模版07-配管报告_tpl.docx",
}

AUDIT_RULES = {
    # checkin_reason → product_type → list of 10 values ("是"/"不适用")
    # 规则：文档入受控库 → 5,6,7项是；代码入受控库 → 5,6,8项是；其余均不适用
    "入受控库": {
        "文档": ["不适用","不适用","不适用","不适用","是","是","是","不适用","不适用","不适用"],
        "代码": ["不适用","不适用","不适用","不适用","是","是","不适用","是","不适用","不适用"],
        "其他": ["不适用","不适用","不适用","不适用","是","是","不适用","不适用","不适用","不适用"],
    },
    "基线发布": {
        "文档": ["是","是","是","是","是","是","是","不适用","不适用","不适用"],
        "代码": ["是","是","是","是","是","是","不适用","是","不适用","不适用"],
        "其他": ["是","是","是","是","是","是","不适用","不适用","不适用","不适用"],
    },
    "基线变更": {
        "文档": ["是","是","是","是","是","是","是","不适用","不适用","不适用"],
        "代码": ["是","是","是","是","是","是","不适用","是","不适用","不适用"],
        "其他": ["是","是","是","是","是","是","不适用","不适用","不适用","不适用"],
    },
    "入产品库": {
        "文档": ["不适用","不适用","不适用","不适用","是","是","是","是","是","是"],
        "代码": ["不适用","不适用","不适用","不适用","是","是","是","是","是","是"],
        "其他": ["不适用","不适用","不适用","不适用","是","是","是","是","是","是"],
    },
}


def _tpl_key(dr: DocumentRecord, activity: Activity) -> str:
    if dr.doc_type == "配置审核":
        name = activity.activity_type.name if activity.activity_type else ""
        return "配置审核_产品级" if name == "产品入库" else "配置审核_阶段级"
    return dr.doc_type


async def _get_activity_products(db: AsyncSession, activity_id: int) -> list[Product]:
    rows = await db.execute(
        select(Product)
        .join(ActivityProduct, ActivityProduct.product_id == Product.id)
        .where(ActivityProduct.activity_id == activity_id)
        .order_by(ActivityProduct.sort_order)
    )
    return rows.scalars().all()


async def _get_baseline_products(db: AsyncSession, baseline_id: int) -> list[Product]:
    rows = await db.execute(
        select(Product)
        .join(BaselineProduct, BaselineProduct.product_id == Product.id)
        .where(BaselineProduct.baseline_id == baseline_id)
        .order_by(BaselineProduct.sort_order)
    )
    return rows.scalars().all()


async def _get_related_doc_number(db: AsyncSession, activity_id: int, doc_type: str) -> str:
    row = await db.execute(
        select(DocumentRecord)
        .where(DocumentRecord.activity_id == activity_id)
        .where(DocumentRecord.doc_type == doc_type)
        .limit(1)
    )
    dr = row.scalar_one_or_none()
    return dr.doc_number if dr else ""


async def _get_baseline_release_number(db: AsyncSession, project_id: int, baseline_id: int) -> str:
    row = await db.execute(
        select(DocumentRecord)
        .join(Activity, Activity.id == DocumentRecord.activity_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .where(Phase.project_id == project_id)
        .where(Activity.baseline_id == baseline_id)
        .where(DocumentRecord.doc_type == "基线发布")
        .limit(1)
    )
    dr = row.scalar_one_or_none()
    return dr.doc_number if dr else ""


async def _build_checkin_ctx(db, dr, activity, proj) -> dict:
    products = await _get_activity_products(db, activity.id)
    is_first = all(p.previous_version in (None, "", "无") for p in products)
    items = [{"name": p.name, "code": p.code, "version": p.version} for p in products]
    product_list_text = "，".join(f"{p.name}{p.version}" for p in products)
    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "is_first_checkin": is_first,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader, "cm_manager": proj.cm_manager},
        "items": items,
        "product_list_text": product_list_text,
    }


async def _build_checkout_ctx(db, dr, activity, proj) -> dict:
    products = await _get_activity_products(db, activity.id)
    items = [{"name": p.name, "code": p.code, "version": p.version} for p in products]
    product_list_text = "，".join(f"{p.name}{p.version}" for p in products)
    reason = activity.checkout_reason or ""
    checkout_type = ""
    for kw in ("使用", "交付", "变更"):
        if kw in reason:
            checkout_type = kw
            break
    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "checkout_type": checkout_type,
        "checkout_reason_text": reason,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader, "cm_manager": proj.cm_manager},
        "items": items,
        "product_list_text": product_list_text,
    }


async def _build_baseline_release_ctx(db, dr, activity, proj) -> dict:
    bl = await db.get(Baseline, activity.baseline_id) if activity.baseline_id else None
    bl_products = await _get_baseline_products(db, bl.id) if bl else []
    items = [{"name": p.name, "code": p.code, "version": p.version} for p in bl_products]
    return {
        "doc_number": dr.doc_number,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader, "cm_manager": proj.cm_manager},
        "baseline": {
            "name": bl.name if bl else "",
            "code": bl.code if bl else "",
            "version": bl.version if bl else "",
            "previous_version": bl.previous_version if bl else None,
            "release_date": bl.release_date if bl else "",
        },
        "items": items,
    }


async def _build_audit_product_ctx(db, dr, activity, proj) -> dict:
    products = await _get_activity_products(db, activity.id)
    checkin_reason = activity.checkin_reason or "入受控库"

    bl = await db.get(Baseline, activity.baseline_id) if activity.baseline_id else None
    baseline_doc_number = ""
    if bl and checkin_reason in ("基线发布", "基线变更"):
        baseline_doc_number = await _get_baseline_release_number(db, proj.id, bl.id)

    checkin_doc_number = await _get_related_doc_number(db, activity.id, "入库申请")

    rule_key = checkin_reason if checkin_reason in AUDIT_RULES else "入受控库"

    product_items = []
    check_list = ["不适用"] * 10
    for p in products:
        pt = p.product_type if p.product_type in AUDIT_RULES[rule_key] else "文档"
        check_list = AUDIT_RULES[rule_key][pt]
        baseline_info = ""
        if bl:
            baseline_info = f"{bl.name} {bl.version}"
        product_items.append({
            "name": p.name,
            "code": p.code,
            "version": p.version,
            "baseline_info": baseline_info,
        })

    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "checkin_reason": checkin_reason,
        "check": check_list,
        "baseline_doc_number": baseline_doc_number,
        "checkin_doc_number": checkin_doc_number,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader,
                    "cm_manager": f"{proj.cm_manager}、{proj.leader}"},
        "products": product_items,
    }


async def _build_audit_phase_ctx(db, dr, activity, proj) -> dict:
    phase = await db.get(Phase, activity.phase_id)
    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader,
                    "cm_manager": proj.cm_manager},
        "phase": {"name": phase.name if phase else "", "start_date": phase.start_date if phase else ""},
    }


async def _get_checkin_products_ordered(db, proj_id: int, cutoff_date: str) -> list:
    """
    返回截止 cutoff_date 已入库的产品列表，按入库活动日期、entry_order 升序。
    每个产品只取最早入库记录，并动态计算该截止日期下的 status 和 previous_version，
    不依赖数据库中的静态字段（静态字段反映全量最终状态，历史文档不适用）。
    返回 SimpleNamespace 列表，支持 p.id / p.name / p.status 等点语法访问。
    """
    rows = await db.execute(
        select(Product, Activity.activity_date, Activity.entry_order)
        .join(ActivityProduct, ActivityProduct.product_id == Product.id)
        .join(Activity, Activity.id == ActivityProduct.activity_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .join(ActivityType, ActivityType.id == Activity.activity_type_id)
        .where(Phase.project_id == proj_id)
        .where(ActivityType.name == "产品入库")
        .where(Activity.activity_date <= cutoff_date)
        .order_by(Activity.activity_date, Activity.entry_order, Product.id)
    )
    seen: set[int] = set()
    products: list[Product] = []
    for prod, _, _ in rows.all():
        if prod.id not in seen:
            seen.add(prod.id)
            products.append(prod)

    # 按 (name, code) 分组，推导截止日期下的动态状态和前向版本
    groups: dict[tuple, list[Product]] = defaultdict(list)
    for prod in products:
        groups[(prod.name, prod.code)].append(prod)

    result = []
    for prod in products:
        group = groups[(prod.name, prod.code)]
        idx = group.index(prod)
        result.append(SimpleNamespace(
            id=prod.id,
            name=prod.name,
            code=prod.code,
            version=prod.version,
            status='有效' if idx == len(group) - 1 else '无效',
            previous_version=group[idx - 1].version if idx > 0 else None,
        ))
    return result


async def _build_cm_list_ctx(db, dr, activity, proj) -> dict:
    # 仅收录入库时间 ≤ 本次配管清单活动日期的配置项，按入库日期排序
    all_products = await _get_checkin_products_ordered(db, proj.id, activity.activity_date)

    # 已发布基线：有发布基线活动且发布日期 ≤ 配管清单活动日期
    published_bl_rows = await db.execute(
        select(Activity.baseline_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .join(ActivityType, ActivityType.id == Activity.activity_type_id)
        .where(Phase.project_id == proj.id)
        .where(ActivityType.name == "发布基线")
        .where(Activity.activity_date <= activity.activity_date)
        .where(Activity.baseline_id.isnot(None))
        .distinct()
    )
    published_bl_ids = {r[0] for r in published_bl_rows.all()}

    # 已发布基线信息
    all_baselines: dict[int, Baseline] = {}
    if published_bl_ids:
        bl_rows = await db.execute(
            select(Baseline).where(Baseline.id.in_(published_bl_ids))
        )
        all_baselines = {bl.id: bl for bl in bl_rows.scalars().all()}

    # 配置项 → 已发布基线列表（一个配置项可能属于多个基线）
    product_to_baselines: dict[int, list[Baseline]] = {}
    if published_bl_ids:
        bp_rows = await db.execute(
            select(BaselineProduct)
            .where(BaselineProduct.baseline_id.in_(published_bl_ids))
        )
        for bp in bp_rows.scalars().all():
            product_to_baselines.setdefault(bp.product_id, []).append(all_baselines[bp.baseline_id])

    items = []
    for p in all_products:
        bls = product_to_baselines.get(p.id, [])
        items.append({
            "name": p.name,
            "code": p.code,
            "version": p.version,
            "previous_version": p.previous_version,
            "status": p.status,
            "baseline_info": "、".join(f"{bl.name} {bl.version}" for bl in bls),
        })

    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader, "cm_manager": proj.cm_manager},
        "products": items,
    }


async def _build_cm_report_ctx(db, dr, activity, proj) -> dict:
    phase = await db.get(Phase, activity.phase_id)

    # 报告时间范围
    start = phase.start_date if phase and phase.start_date else ""
    end = phase.end_date if phase and phase.end_date else ""
    date_range = f"{start}～{end}" if start and end else start or end

    async def _bl_ids_published_in(date_from: str | None, date_to: str | None) -> set[int]:
        """查出在 [date_from, date_to] 范围内有发布活动的基线 ID 集合"""
        q = (
            select(Activity.baseline_id)
            .join(Phase, Phase.id == Activity.phase_id)
            .join(ActivityType, ActivityType.id == Activity.activity_type_id)
            .where(Phase.project_id == proj.id)
            .where(ActivityType.name == "发布基线")
            .where(Activity.baseline_id.isnot(None))
        )
        if date_from:
            q = q.where(Activity.activity_date >= date_from)
        if date_to:
            q = q.where(Activity.activity_date <= date_to)
        rows = await db.execute(q.distinct())
        return {r[0] for r in rows.all()}

    # 基线建立情况：本阶段期间（start～end）内发布的基线
    phase_bl_ids = await _bl_ids_published_in(start or None, end or None)

    # 当前有效基线：不晚于配管报告活动日期已发布的所有基线
    current_bl_ids = await _bl_ids_published_in(None, activity.activity_date)

    async def _fetch_baselines(bl_ids: set[int]) -> list[Baseline]:
        if not bl_ids:
            return []
        rows = await db.execute(
            select(Baseline).where(Baseline.id.in_(bl_ids)).order_by(Baseline.created_at)
        )
        return rows.scalars().all()

    phase_baselines_list = await _fetch_baselines(phase_bl_ids)
    current_baselines_list = await _fetch_baselines(current_bl_ids)

    phase_baselines = [
        {"name": bl.name, "code": bl.code, "version": bl.version,
         "release_date": bl.release_date or "", "status": bl.status}
        for bl in phase_baselines_list
    ]

    # 仅收录入库时间 ≤ 配管报告活动日期的配置项，按入库日期排序（与配管清单逻辑一致）
    checked_products = await _get_checkin_products_ordered(db, proj.id, activity.activity_date)
    all_products = [
        {"name": p.name, "code": p.code, "version": p.version, "status": p.status}
        for p in checked_products
    ]

    # 当前有效基线-产品交叉行（用 current_baselines_list）
    baseline_product_rows = []
    for bl in current_baselines_list:
        bl_prods = await _get_baseline_products(db, bl.id)
        for p in bl_prods:
            baseline_product_rows.append({
                "baseline_name": bl.name,
                "baseline_version": bl.version,
                "product_name": p.name,
                "product_code": p.code,
                "product_version": p.version,
            })

    # 配置审核情况：本阶段所有产品入库活动（产品级审核）
    checkin_rows = await db.execute(
        select(Activity, ActivityType)
        .join(ActivityType, ActivityType.id == Activity.activity_type_id)
        .where(Activity.phase_id == (phase.id if phase else -1))
        .where(ActivityType.name == "产品入库")
        .order_by(Activity.activity_date)
    )
    phase_audit_reports = []
    for act, _ in checkin_rows.all():
        prods = await _get_activity_products(db, act.id)
        phase_audit_reports.append({
            "activity_date": act.activity_date,
            "product_names": "、".join(p.name for p in prods),
        })

    return {
        "doc_number": dr.doc_number,
        "activity_date": activity.activity_date,
        "project": {"name": proj.name, "code": proj.code, "version": proj.version, "leader": proj.leader, "cm_manager": proj.cm_manager},
        "phase": {"name": phase.name if phase else "", "start_date": date_range},
        "phase_baselines": phase_baselines,
        "all_products": all_products,
        "baseline_product_rows": baseline_product_rows,
        "phase_audit_reports": phase_audit_reports,
    }


CONTEXT_BUILDERS = {
    "入库申请":       _build_checkin_ctx,
    "出库申请":       _build_checkout_ctx,
    "基线发布":       _build_baseline_release_ctx,
    "配置审核_产品级": _build_audit_product_ctx,
    "配置审核_阶段级": _build_audit_phase_ctx,
    "配管清单":       _build_cm_list_ctx,
    "配管报告":       _build_cm_report_ctx,
}


async def generate_document(
    db: AsyncSession,
    dr: DocumentRecord,
    activity: Activity,
    proj: Project,
) -> str:
    if activity.activity_type is None:
        activity.activity_type = await db.get(ActivityType, activity.activity_type_id)

    key = _tpl_key(dr, activity)
    tpl_path = TPL_DIR / TPL_MAP[key]
    context = await CONTEXT_BUILDERS[key](db, dr, activity, proj)

    tpl = DocxTemplate(str(tpl_path))
    tpl.render(context)

    # 计算阶段在项目内的序号（按 phase.id 升序排列）
    phase = await db.get(Phase, activity.phase_id)
    phase_rows = await db.execute(
        select(Phase.id).where(Phase.project_id == proj.id).order_by(Phase.id)
    )
    phase_ids = [row[0] for row in phase_rows.all()]
    phase_seq = phase_ids.index(activity.phase_id) + 1 if activity.phase_id in phase_ids else 0
    date_tag = (activity.activity_date or "").replace("-", "")
    out_path = document_path(
        GEN_DIR, f"{proj.name}ZDPX{proj.code}",
        f"{phase_seq:02d}-{phase.name if phase else '未知阶段'}",
        f"{dr.doc_number}({date_tag})", proj.id, activity.phase_id, dr.id,
    )
    save_document(tpl, out_path)

    dr.file_path = str(out_path)
    dr.generated_at = datetime.utcnow().isoformat()
    dr.is_stale = 0
    return str(out_path)


async def batch_generate_project(db: AsyncSession, proj: Project) -> list[DocumentRecord]:
    rows = await db.execute(
        select(DocumentRecord)
        .join(Activity, Activity.id == DocumentRecord.activity_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .where(Phase.project_id == proj.id)
    )
    records = rows.scalars().all()

    for dr in records:
        activity = await db.get(Activity, dr.activity_id)
        activity.activity_type = await db.get(ActivityType, activity.activity_type_id)
        phase = await db.get(Phase, activity.phase_id)
        await generate_document(db, dr, activity, proj)

    return records
