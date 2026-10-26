from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from app.core.database import init_db
from app.models.seed import seed_activity_types
from app.core.database import AsyncSessionLocal, engine
from app.core.output_paths import DocumentOutputError

from app.api.routes import projects, phases, activities, products, baselines, documents, activity_types, importer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_activity_types(db)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="ConfigM", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.exception_handler(DocumentOutputError)
async def document_output_error(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app.include_router(projects.router)
app.include_router(phases.router)
app.include_router(activities.router)
app.include_router(products.router)
app.include_router(baselines.router)
app.include_router(documents.router)
app.include_router(activity_types.router)
app.include_router(importer.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(str(STATIC_DIR / "templates" / "index.html"))
