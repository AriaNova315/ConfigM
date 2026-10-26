from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import io

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.importer import parse_excel, execute_import, build_export, _pending

router = APIRouter(tags=["import-export"])


@router.post("/api/import/parse")
async def import_parse(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xlsm')):
        raise HTTPException(400, "请上传 .xlsx 格式文件")
    content = await file.read()
    try:
        data = parse_excel(content)
    except Exception as e:
        raise HTTPException(400, f"解析失败：{e}")

    _pending['data'] = data
    return {
        'project': data['project'],
        'summary': {
            'products': len(data['products']),
            'baselines': len(data['baselines']),
            'phases': len([p for p in data['phases'] if p['activities']]),
            'activities': sum(len(p['activities']) for p in data['phases']),
        },
        'needs_checkin': data['needs_checkin'],
        'needs_checkout': data['needs_checkout'],
        'needs_baseline': data['needs_baseline'],
        'baseline_names': [b['name'] for b in data['baselines']],
    }


@router.post("/api/import/confirm")
async def import_confirm(body: dict, db: AsyncSession = Depends(get_db)):
    if 'data' not in _pending:
        raise HTTPException(400, "请先上传并解析 Excel 文件")
    data = _pending.pop('data')

    checkin_reasons: dict[str, str] = body.get('checkin_reasons', {})
    checkout_reasons: dict[str, str] = body.get('checkout_reasons', {})
    baseline_selections: dict[str, str] = body.get('baseline_selections', {})

    try:
        result = await execute_import(db, data, checkin_reasons, checkout_reasons, baseline_selections)
    except Exception as e:
        raise HTTPException(500, f"导入失败：{e}")

    return result


@router.get("/api/export")
async def export_excel(db: AsyncSession = Depends(get_db)):
    content = await build_export(db)
    if not content:
        raise HTTPException(404, "暂无数据可导出")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename*=utf-8''ConfigM_export.xlsx",
            "Cache-Control": "no-store",
        },
    )
