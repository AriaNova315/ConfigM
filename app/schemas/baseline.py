from pydantic import BaseModel


class BaselineCreate(BaseModel):
    name: str
    code: str
    version: str
    previous_version: str | None = None
    release_date: str | None = None
    status: str = "有效"


class BaselineUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    version: str | None = None
    previous_version: str | None = None
    release_date: str | None = None
    status: str | None = None


class BaselineProductAdd(BaseModel):
    product_id: int
    sort_order: int = 0


class BaselineProductOut(BaseModel):
    id: int
    name: str
    code: str
    version: str
    product_type: str

    model_config = {"from_attributes": True}


class BaselineOut(BaseModel):
    id: int
    project_id: int
    name: str
    code: str
    version: str
    previous_version: str | None
    release_date: str | None
    status: str
    products: list[BaselineProductOut] = []
    created_at: str

    model_config = {"from_attributes": True}
