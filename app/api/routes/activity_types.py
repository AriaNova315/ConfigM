from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import ActivityType
import json

router = APIRouter(tags=["activity_types"])


class ActivityTypeOut(BaseModel):
    id: int
    name: str
    domain: str
    doc_types: list[str]

    model_config = {"from_attributes": True}


@router.get("/api/activity-types", response_model=list[ActivityTypeOut])
async def list_activity_types(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(ActivityType).order_by(ActivityType.id))
    return [
        ActivityTypeOut(id=at.id, name=at.name, domain=at.domain, doc_types=json.loads(at.doc_types))
        for at in rows.scalars().all()
    ]
