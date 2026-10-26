from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Activity, ActivityProduct, ActivityType, DocumentRecord, Phase, Project
from app.schemas.activity import (
    ActivityCreate, ActivityUpdate, ActivityOut,
    ActivityCreateResponse, PreassignedNumber, ReorderWarning,
)
from app.services.sequence import assign_numbers_for_activity, recompute_sequences

router = APIRouter(tags=["activities"])


async def _build_activity_out(activity: Activity, db: AsyncSession) -> ActivityOut:
    # 关联产品 ids
    rows = await db.execute(
        select(ActivityProduct.product_id)
        .where(ActivityProduct.activity_id == activity.id)
        .order_by(ActivityProduct.sort_order)
    )
    product_ids = [r[0] for r in rows.all()]

    # 预分配编号
    dr_rows = await db.execute(
        select(DocumentRecord).where(DocumentRecord.activity_id == activity.id)
    )
    preassigned = [
        PreassignedNumber(doc_type=dr.doc_type, doc_number=dr.doc_number)
        for dr in dr_rows.scalars().all()
    ]

    at = await db.get(ActivityType, activity.activity_type_id)
    return ActivityOut(
        id=activity.id,
        phase_id=activity.phase_id,
        activity_type_id=activity.activity_type_id,
        activity_type_name=at.name if at else "",
        activity_date=activity.activity_date,
        notes=activity.notes,
        checkin_reason=activity.checkin_reason,
        baseline_id=activity.baseline_id,
        checkout_reason=activity.checkout_reason,
        product_ids=product_ids,
        preassigned_numbers=preassigned,
        created_at=activity.created_at,
    )


@router.get("/api/phases/{pid}/activities", response_model=list[ActivityOut])
async def list_activities(pid: int, db: AsyncSession = Depends(get_db)):
    phase = await db.get(Phase, pid)
    if not phase:
        raise HTTPException(404, "阶段不存在")
    rows = await db.execute(
        select(Activity)
        .where(Activity.phase_id == pid)
        .order_by(Activity.activity_date, Activity.entry_order)
    )
    activities = rows.scalars().all()
    return [await _build_activity_out(a, db) for a in activities]


@router.post("/api/phases/{pid}/activities", response_model=ActivityCreateResponse, status_code=201)
async def create_activity(pid: int, body: ActivityCreate, db: AsyncSession = Depends(get_db)):
    phase = await db.get(Phase, pid)
    if not phase:
        raise HTTPException(404, "阶段不存在")
    proj = await db.get(Project, phase.project_id)

    # 计算 entry_order（同日同类型最大值+1）
    max_order = await db.execute(
        select(Activity.entry_order)
        .where(Activity.phase_id == pid)
        .where(Activity.activity_type_id == body.activity_type_id)
        .where(Activity.activity_date == body.activity_date)
        .order_by(Activity.entry_order.desc())
        .limit(1)
    )
    max_val = max_order.scalar_one_or_none()
    entry_order = (max_val or 0) + 1

    activity = Activity(
        phase_id=pid,
        activity_type_id=body.activity_type_id,
        activity_date=body.activity_date,
        notes=body.notes,
        checkin_reason=body.checkin_reason,
        baseline_id=body.baseline_id,
        checkout_reason=body.checkout_reason,
        entry_order=entry_order,
    )
    db.add(activity)
    await db.flush()

    # 关联产品
    for order, pid_prod in enumerate(body.product_ids):
        db.add(ActivityProduct(activity_id=activity.id, product_id=pid_prod, sort_order=order))
    await db.flush()

    # 预分配编号
    preassigned, warnings = await assign_numbers_for_activity(db, activity, proj.id, proj.code, proj.version)
    await db.commit()
    await db.refresh(activity)

    act_out = await _build_activity_out(activity, db)
    return ActivityCreateResponse(
        activity=act_out,
        reorder_warnings=[ReorderWarning(**w) for w in warnings],
    )


@router.put("/api/activities/{id}", response_model=ActivityCreateResponse)
async def update_activity(id: int, body: ActivityUpdate, db: AsyncSession = Depends(get_db)):
    activity = await db.get(Activity, id)
    if not activity:
        raise HTTPException(404, "活动不存在")
    phase = await db.get(Phase, activity.phase_id)
    proj = await db.get(Project, phase.project_id)

    for k, v in body.model_dump(exclude={"product_ids"}, exclude_none=True).items():
        setattr(activity, k, v)

    if body.product_ids is not None:
        await db.execute(
            ActivityProduct.__table__.delete().where(ActivityProduct.activity_id == id)
        )
        for order, pid_prod in enumerate(body.product_ids):
            db.add(ActivityProduct(activity_id=id, product_id=pid_prod, sort_order=order))

    await db.flush()

    # 重算流水号
    import json
    at = await db.get(ActivityType, activity.activity_type_id)
    doc_types = json.loads(at.doc_types)
    all_warnings = []
    for dt in doc_types:
        w = await recompute_sequences(db, proj.id, dt, proj.code, proj.version)
        all_warnings.extend(w)

    await db.commit()
    await db.refresh(activity)
    act_out = await _build_activity_out(activity, db)
    return ActivityCreateResponse(
        activity=act_out,
        reorder_warnings=[ReorderWarning(**w) for w in all_warnings],
    )


@router.delete("/api/activities/{id}", status_code=204)
async def delete_activity(id: int, db: AsyncSession = Depends(get_db)):
    activity = await db.get(Activity, id)
    if not activity:
        raise HTTPException(404, "活动不存在")
    phase = await db.get(Phase, activity.phase_id)
    proj = await db.get(Project, phase.project_id)

    import json
    at = await db.get(ActivityType, activity.activity_type_id)
    doc_types = json.loads(at.doc_types)

    await db.delete(activity)
    await db.flush()

    for dt in doc_types:
        await recompute_sequences(db, proj.id, dt, proj.code, proj.version)

    await db.commit()
