from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    code: str
    version: str
    previous_version: str | None = None
    product_type: str = "文档"          # 文档/代码/其他
    status: str = "有效"


class ProductUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    version: str | None = None
    previous_version: str | None = None
    product_type: str | None = None
    status: str | None = None


class ProductOut(BaseModel):
    id: int
    project_id: int
    name: str
    code: str
    version: str
    previous_version: str | None
    product_type: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}
