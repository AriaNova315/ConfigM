from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Product, Project
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(tags=["products"])


@router.get("/api/projects/{pid}/products", response_model=list[ProductOut])
async def list_products(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    rows = await db.execute(
        select(Product).where(Product.project_id == pid).order_by(Product.created_at)
    )
    return rows.scalars().all()


@router.post("/api/projects/{pid}/products", response_model=ProductOut, status_code=201)
async def create_product(pid: int, body: ProductCreate, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    product = Product(project_id=pid, **body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/api/products/{id}", response_model=ProductOut)
async def update_product(id: int, body: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, id)
    if not product:
        raise HTTPException(404, "产品不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(product, k, v)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/api/products/{id}", status_code=204)
async def delete_product(id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, id)
    if not product:
        raise HTTPException(404, "产品不存在")
    await db.delete(product)
    await db.commit()
