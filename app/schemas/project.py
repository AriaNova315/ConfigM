from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    code: str
    version: str = "0.0"
    leader: str
    cm_manager: str


class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    version: str | None = None
    leader: str | None = None
    cm_manager: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    code: str
    version: str
    leader: str
    cm_manager: str
    created_at: str

    model_config = {"from_attributes": True}
