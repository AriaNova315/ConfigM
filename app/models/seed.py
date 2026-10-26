"""数据库初始数据：预置活动类型。"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import ActivityType

ACTIVITY_TYPES = [
    {"name": "配置状态纪实", "domain": "配置管理", "doc_types": ["配管清单"]},
    {"name": "产品入库",     "domain": "配置管理", "doc_types": ["入库申请", "配置审核"]},
    {"name": "发布基线",     "domain": "配置管理", "doc_types": ["基线发布"]},
    {"name": "配置管理报告", "domain": "配置管理", "doc_types": ["配置审核", "配管报告"]},
    {"name": "产品出库",     "domain": "配置管理", "doc_types": ["出库申请"]},
]


async def seed_activity_types(db: AsyncSession):
    for item in ACTIVITY_TYPES:
        result = await db.execute(select(ActivityType).where(ActivityType.name == item["name"]))
        if result.scalar_one_or_none() is None:
            db.add(ActivityType(
                name=item["name"],
                domain=item["domain"],
                doc_types=json.dumps(item["doc_types"], ensure_ascii=False),
            ))
    await db.commit()
