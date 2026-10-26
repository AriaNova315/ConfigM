from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, Boolean, ForeignKey,
    UniqueConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)          # 纯数字项目代号
    version: Mapped[str] = mapped_column(String, nullable=False, default="0.0")  # 项目版本，如 0.0
    leader: Mapped[str] = mapped_column(String, nullable=False)        # 项目组长
    cm_manager: Mapped[str] = mapped_column(String, nullable=False)    # 配置管理员
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    phases: Mapped[list["Phase"]] = relationship("Phase", back_populates="project", cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="project", cascade="all, delete-orphan")
    baselines: Mapped[list["Baseline"]] = relationship("Baseline", back_populates="project", cascade="all, delete-orphan")
    document_records: Mapped[list["DocumentRecord"]] = relationship("DocumentRecord", back_populates="project", cascade="all, delete-orphan")


class Phase(Base):
    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[str | None] = mapped_column(String)             # YYYY-MM-DD
    end_date: Mapped[str | None] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    project: Mapped["Project"] = relationship("Project", back_populates="phases")
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="phase", cascade="all, delete-orphan")


class ActivityType(Base):
    __tablename__ = "activity_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    doc_types: Mapped[str] = mapped_column(Text, nullable=False)       # JSON 数组

    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="activity_type")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase_id: Mapped[int] = mapped_column(Integer, ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    activity_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("activity_types.id"), nullable=False)
    activity_date: Mapped[str] = mapped_column(String, nullable=False) # YYYY-MM-DD
    notes: Mapped[str | None] = mapped_column(Text)

    # 产品入库专用
    checkin_reason: Mapped[str | None] = mapped_column(String)         # 入受控库/基线发布/基线变更/产品入库
    baseline_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("baselines.id"))

    # 产品出库专用
    checkout_reason: Mapped[str | None] = mapped_column(Text)          # 自由文本

    entry_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    phase: Mapped["Phase"] = relationship("Phase", back_populates="activities")
    activity_type: Mapped["ActivityType"] = relationship("ActivityType", back_populates="activities")
    baseline: Mapped["Baseline | None"] = relationship("Baseline", foreign_keys=[baseline_id])
    activity_products: Mapped[list["ActivityProduct"]] = relationship("ActivityProduct", back_populates="activity", cascade="all, delete-orphan")
    document_records: Mapped[list["DocumentRecord"]] = relationship("DocumentRecord", back_populates="activity")

    __table_args__ = (
        Index("idx_activities_phase_date", "phase_id", "activity_date"),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)          # 产品标识
    version: Mapped[str] = mapped_column(String, nullable=False)
    previous_version: Mapped[str | None] = mapped_column(String)
    product_type: Mapped[str] = mapped_column(String, default="文档")  # 文档/代码/其他
    status: Mapped[str] = mapped_column(String, default="有效")        # 有效/无效
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    project: Mapped["Project"] = relationship("Project", back_populates="products")
    activity_products: Mapped[list["ActivityProduct"]] = relationship("ActivityProduct", back_populates="product", cascade="all, delete-orphan")
    baseline_products: Mapped[list["BaselineProduct"]] = relationship("BaselineProduct", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_products_project", "project_id"),
    )


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)          # 基线名称
    code: Mapped[str] = mapped_column(String, nullable=False)          # 标识代码，如 BL-FP
    version: Mapped[str] = mapped_column(String, nullable=False)
    previous_version: Mapped[str | None] = mapped_column(String)
    release_date: Mapped[str | None] = mapped_column(String)           # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String, default="有效")        # 有效/无效
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    project: Mapped["Project"] = relationship("Project", back_populates="baselines")
    baseline_products: Mapped[list["BaselineProduct"]] = relationship("BaselineProduct", back_populates="baseline", cascade="all, delete-orphan")


class BaselineProduct(Base):
    __tablename__ = "baseline_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baseline_id: Mapped[int] = mapped_column(Integer, ForeignKey("baselines.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    baseline: Mapped["Baseline"] = relationship("Baseline", back_populates="baseline_products")
    product: Mapped["Product"] = relationship("Product", back_populates="baseline_products")

    __table_args__ = (UniqueConstraint("baseline_id", "product_id"),)


class ActivityProduct(Base):
    __tablename__ = "activity_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="activity_products")
    product: Mapped["Product"] = relationship("Product", back_populates="activity_products")

    __table_args__ = (
        Index("idx_activity_products_activity", "activity_id"),
    )


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    activity_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("activities.id"))
    doc_type: Mapped[str] = mapped_column(String, nullable=False)      # 入库申请/出库申请/基线发布/配置审核/配管清单/配管报告
    doc_number: Mapped[str] = mapped_column(String, nullable=False)    # ZDPX-2021163-配置管理-入库申请-001
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[str | None] = mapped_column(String)           # NULL=未生成
    file_path: Mapped[str | None] = mapped_column(String)
    is_stale: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    project: Mapped["Project"] = relationship("Project", back_populates="document_records")
    activity: Mapped["Activity | None"] = relationship("Activity", back_populates="document_records")

    __table_args__ = (
        UniqueConstraint("project_id", "doc_type", "sequence"),
        Index("idx_doc_records_project_type", "project_id", "doc_type"),
    )
