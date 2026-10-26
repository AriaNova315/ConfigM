import io
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import ActivityType, DocumentRecord, Activity, Phase, Project
from app.schemas.document import DocumentRecordOut
from app.services.generator import generate_document, batch_generate_project

router = APIRouter(tags=["documents"])


@router.get("/api/projects/{pid}/documents", response_model=list[DocumentRecordOut])
async def list_documents(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    rows = await db.execute(
        select(DocumentRecord)
        .join(Activity, Activity.id == DocumentRecord.activity_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .where(Phase.project_id == pid)
        .order_by(DocumentRecord.doc_type, DocumentRecord.sequence)
    )
    return rows.scalars().all()


@router.post("/api/documents/{doc_id}/generate", response_model=DocumentRecordOut)
async def generate_single(doc_id: int, db: AsyncSession = Depends(get_db)):
    dr = await db.get(DocumentRecord, doc_id)
    if not dr:
        raise HTTPException(404, "文档记录不存在")
    activity = await db.get(Activity, dr.activity_id)
    activity.activity_type = await db.get(ActivityType, activity.activity_type_id)
    phase = await db.get(Phase, activity.phase_id)
    proj = await db.get(Project, phase.project_id)

    await generate_document(db, dr, activity, proj)
    # generate_document already sets generated_at and is_stale on dr
    await db.commit()
    await db.refresh(dr)
    return dr


@router.post("/api/projects/{pid}/generate-all", response_model=list[DocumentRecordOut])
async def generate_all(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    records = await batch_generate_project(db, proj)
    await db.commit()
    return records


@router.get("/api/projects/{pid}/download-all")
async def download_all_documents(pid: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, pid)
    if not proj:
        raise HTTPException(404, "项目不存在")
    rows = await db.execute(
        select(DocumentRecord)
        .join(Activity, Activity.id == DocumentRecord.activity_id)
        .join(Phase, Phase.id == Activity.phase_id)
        .where(Phase.project_id == pid)
        .where(DocumentRecord.file_path.isnot(None))
    )
    records = rows.scalars().all()
    generated = [dr for dr in records if dr.file_path and os.path.exists(dr.file_path)]
    if not generated:
        raise HTTPException(404, "暂无已生成的文档")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dr in generated:
            zf.write(dr.file_path, os.path.basename(dr.file_path))
    buf.seek(0)

    safe_name = f"ConfigM_{proj.code}_documents.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{safe_name}",
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/documents/{doc_id}/download")
async def download_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    dr = await db.get(DocumentRecord, doc_id)
    if not dr or not dr.file_path:
        raise HTTPException(404, "文件不存在，请先生成")
    import os
    if not os.path.exists(dr.file_path):
        raise HTTPException(404, "文件已丢失，请重新生成")
    return FileResponse(
        dr.file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(dr.file_path),
        headers={"Cache-Control": "no-store"},
    )
