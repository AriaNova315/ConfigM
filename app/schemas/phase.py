from pydantic import BaseModel


class PhaseCreate(BaseModel):
    name: str
    start_date: str | None = None
    end_date: str | None = None
    sort_order: int = 0


class PhaseUpdate(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    sort_order: int | None = None


class PhaseOut(BaseModel):
    id: int
    project_id: int
    name: str
    start_date: str | None
    end_date: str | None
    sort_order: int
    created_at: str

    model_config = {"from_attributes": True}


class PhaseReorder(BaseModel):
    phase_ids: list[int]
