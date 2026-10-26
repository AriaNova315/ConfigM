from pydantic import BaseModel


class ActivityCreate(BaseModel):
    activity_type_id: int
    activity_date: str                  # YYYY-MM-DD
    notes: str | None = None
    checkin_reason: str | None = None   # 产品入库专用
    baseline_id: int | None = None
    checkout_reason: str | None = None  # 产品出库专用
    product_ids: list[int] = []         # 关联产品


class ActivityUpdate(BaseModel):
    activity_date: str | None = None
    notes: str | None = None
    checkin_reason: str | None = None
    baseline_id: int | None = None
    checkout_reason: str | None = None
    product_ids: list[int] | None = None


class PreassignedNumber(BaseModel):
    doc_type: str
    doc_number: str


class ReorderWarning(BaseModel):
    doc_number: str
    old_seq: int
    new_seq: int


class ActivityOut(BaseModel):
    id: int
    phase_id: int
    activity_type_id: int
    activity_type_name: str
    activity_date: str
    notes: str | None
    checkin_reason: str | None
    baseline_id: int | None
    checkout_reason: str | None
    product_ids: list[int]
    preassigned_numbers: list[PreassignedNumber]
    created_at: str

    model_config = {"from_attributes": True}


class ActivityCreateResponse(BaseModel):
    activity: ActivityOut
    reorder_warnings: list[ReorderWarning] = []
