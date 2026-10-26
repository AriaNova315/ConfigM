from pydantic import BaseModel


class DocumentRecordOut(BaseModel):
    id: int
    project_id: int
    activity_id: int | None
    doc_type: str
    doc_number: str
    sequence: int
    generated_at: str | None
    file_path: str | None
    is_stale: int
    created_at: str

    model_config = {"from_attributes": True}
