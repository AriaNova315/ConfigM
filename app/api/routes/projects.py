from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return rows.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    proj = Project(**body.model_dump())
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj


@router.get("/{pid}", response_model=ProjectOut)
async def get_project(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    return proj


@router.put("/{pid}", response_model=ProjectOut)
async def update_project(pid: int, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(proj, k, v)
    await db.commit()
    await db.refresh(proj)
    return proj


@router.delete("/{pid}", status_code=204)
async def delete_project(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    await db.delete(proj)
    await db.commit()
