from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Baseline, BaselineProduct, Product, Project
from app.schemas.baseline import (
    BaselineCreate, BaselineUpdate, BaselineOut,
    BaselineProductAdd, BaselineProductOut,
)

router = APIRouter(tags=["baselines"])


async def _baseline_out(baseline: Baseline, db: AsyncSession) -> BaselineOut:
    rows = await db.execute(
        select(Product)
        .join(BaselineProduct, BaselineProduct.product_id == Product.id)
        .where(BaselineProduct.baseline_id == baseline.id)
        .order_by(BaselineProduct.sort_order)
    )
    products = [
        BaselineProductOut(
            id=p.id, name=p.name, code=p.code,
            version=p.version, product_type=p.product_type,
        )
        for p in rows.scalars().all()
    ]
    return BaselineOut(
        id=baseline.id,
        project_id=baseline.project_id,
        name=baseline.name,
        code=baseline.code,
        version=baseline.version,
        previous_version=baseline.previous_version,
        release_date=baseline.release_date,
        status=baseline.status,
        products=products,
        created_at=baseline.created_at,
    )


@router.get("/api/projects/{pid}/baselines", response_model=list[BaselineOut])
async def list_baselines(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    rows = await db.execute(
        select(Baseline).where(Baseline.project_id == pid).order_by(Baseline.created_at)
    )
    return [await _baseline_out(b, db) for b in rows.scalars().all()]


@router.post("/api/projects/{pid}/baselines", response_model=BaselineOut, status_code=201)
async def create_baseline(pid: int, body: BaselineCreate, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    baseline = Baseline(project_id=pid, **body.model_dump())
    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return await _baseline_out(baseline, db)


@router.put("/api/baselines/{id}", response_model=BaselineOut)
async def update_baseline(id: int, body: BaselineUpdate, db: AsyncSession = Depends(get_db)):
    baseline = await db.get(Baseline, id)
    if not baseline:
        raise HTTPException(404, "基线不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(baseline, k, v)
    await db.commit()
    await db.refresh(baseline)
    return await _baseline_out(baseline, db)


@router.delete("/api/baselines/{id}", status_code=204)
async def delete_baseline(id: int, db: AsyncSession = Depends(get_db)):
    baseline = await db.get(Baseline, id)
    if not baseline:
        raise HTTPException(404, "基线不存在")
    await db.delete(baseline)
    await db.commit()


@router.post("/api/baselines/{id}/products", response_model=BaselineOut, status_code=201)
async def add_product_to_baseline(id: int, body: BaselineProductAdd, db: AsyncSession = Depends(get_db)):
    baseline = await db.get(Baseline, id)
    if not baseline:
        raise HTTPException(404, "基线不存在")
    db.add(BaselineProduct(baseline_id=id, product_id=body.product_id, sort_order=body.sort_order))
    await db.commit()
    await db.refresh(baseline)
    return await _baseline_out(baseline, db)


@router.delete("/api/baselines/{id}/products/{pid}", status_code=204)
async def remove_product_from_baseline(id: int, pid: int, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        select(BaselineProduct)
        .where(BaselineProduct.baseline_id == id, BaselineProduct.product_id == pid)
    )
    bp = row.scalar_one_or_none()
    if not bp:
        raise HTTPException(404, "关联不存在")
    await db.delete(bp)
    await db.commit()
