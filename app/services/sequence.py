"""
流水号预分配引擎。
规则：ZDPX-{project_code}/{project_version}-配置管理-{doc_type}-{三位流水号}
流水号按活动日期升序排列，同日同类型按 entry_order 排列。
"""
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Activity, ActivityType, DocumentRecord, Phase


DOC_TYPE_LABEL = {
    "入库申请": "入库申请",
    "出库申请": "出库申请",
    "基线发布": "基线发布",
    "配置审核": "配置审核",
    "配管清单": "配置清单",
    "配管报告": "配置报告",
}


def make_doc_number(project_code: str, project_version: str, doc_type: str, seq: int) -> str:
    label = DOC_TYPE_LABEL.get(doc_type, doc_type)
    return f"ZDPX-{project_code}/{project_version}-配置管理-{label}-{seq:03d}"


async def recompute_sequences(
    db: AsyncSession,
    project_id: int,
    doc_type: str,
    project_code: str,
    project_version: str,
) -> list[dict]:
    stmt = (
        select(DocumentRecord, Activity)
        .join(Activity, DocumentRecord.activity_id == Activity.id, isouter=True)
        .where(DocumentRecord.project_id == project_id)
        .where(DocumentRecord.doc_type == doc_type)
        .order_by(Activity.activity_date, Activity.entry_order, DocumentRecord.id)
    )
    rows = (await db.execute(stmt)).all()

    warnings = []
    to_update: list[tuple] = []
    for new_seq, (dr, _) in enumerate(rows, start=1):
        new_num = make_doc_number(project_code, project_version, doc_type, new_seq)
        if dr.sequence != new_seq or dr.doc_number != new_num:
            old_num = dr.doc_number
            to_update.append((dr, new_seq, new_num))
            if dr.generated_at is not None:
                dr.is_stale = 1
                warnings.append({"doc_number": old_num, "old_seq": new_seq, "new_seq": new_seq})

    if to_update:
        # 先设负数临时序号，避免重排时 SQLite 逐行检查 UNIQUE 约束报冲突
        for dr, _, _ in to_update:
            dr.sequence = -(dr.id)
            dr.doc_number = ""
        await db.flush()
        for dr, new_seq, new_num in to_update:
            dr.sequence = new_seq
            dr.doc_number = new_num
        await db.flush()

    return warnings


async def assign_numbers_for_activity(
    db: AsyncSession,
    activity: Activity,
    project_id: int,
    project_code: str,
    project_version: str,
) -> tuple[list[dict], list[dict]]:
    at = await db.get(ActivityType, activity.activity_type_id)
    doc_types: list[str] = json.loads(at.doc_types)

    all_warnings = []
    preassigned = []

    for doc_type in doc_types:
        existing = await db.execute(
            select(DocumentRecord).where(
                DocumentRecord.activity_id == activity.id,
                DocumentRecord.doc_type == doc_type,
            )
        )
        dr = existing.scalar_one_or_none()

        if dr is None:
            dr = DocumentRecord(
                project_id=project_id,
                activity_id=activity.id,
                doc_type=doc_type,
                doc_number="",
                sequence=0,
            )
            db.add(dr)
            await db.flush()

        warnings = await recompute_sequences(db, project_id, doc_type, project_code, project_version)
        all_warnings.extend(warnings)

        await db.refresh(dr)
        preassigned.append({"doc_type": doc_type, "doc_number": dr.doc_number})

    return preassigned, all_warnings
