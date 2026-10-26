from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Phase, Project
from app.schemas.phase import PhaseCreate, PhaseUpdate, PhaseOut, PhaseReorder

router = APIRouter(tags=["phases"])


@router.get("/api/projects/{pid}/phases", response_model=list[PhaseOut])
async def list_phases(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    rows = await db.execute(
        select(Phase).where(Phase.project_id == pid).order_by(Phase.sort_order, Phase.id)
    )
    return rows.scalars().all()


@router.post("/api/projects/{pid}/phases", response_model=PhaseOut, status_code=201)
async def create_phase(pid: int, body: PhaseCreate, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    phase = Phase(project_id=pid, **body.model_dump())
    db.add(phase)
    await db.commit()
    await db.refresh(phase)
    return phase


@router.put("/api/phases/{id}", response_model=PhaseOut)
async def update_phase(id: int, body: PhaseUpdate, db: AsyncSession = Depends(get_db)):
    phase = await db.get(Phase, id)
    if not phase:
        raise HTTPException(404, "阶段不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(phase, k, v)
    await db.commit()
    await db.refresh(phase)
    return phase


@router.delete("/api/phases/{id}", status_code=204)
async def delete_phase(id: int, db: AsyncSession = Depends(get_db)):
    phase = await db.get(Phase, id)
    if not phase:
        raise HTTPException(404, "阶段不存在")
    await db.delete(phase)
    await db.commit()


@router.put("/api/projects/{pid}/phases/reorder", response_model=list[PhaseOut])
async def reorder_phases(pid: int, body: PhaseReorder, db: AsyncSession = Depends(get_db)):
    for order, phase_id in enumerate(body.phase_ids):
        phase = await db.get(Phase, phase_id)
        if phase and phase.project_id == pid:
            phase.sort_order = order
    await db.commit()
    rows = await db.execute(
        select(Phase).where(Phase.project_id == pid).order_by(Phase.sort_order, Phase.id)
    )
    return rows.scalars().all()
