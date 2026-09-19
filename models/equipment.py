from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, Integer, String
from models.base import Base
from models.lab import Lab


class Equipment(Base):
    __tablename__ = "equipments"
    __table_args__ = {"comment": "实验室设备表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lab_id: Mapped[int] = mapped_column(Integer, index=True, comment="所属实验室", nullable=False)
    name: Mapped[str] = mapped_column(String(50), comment="设备名称", nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), comment="说明", nullable=True)
    img: Mapped[str | None] = mapped_column(String(200), comment="图片", nullable=True)
    spec: Mapped[str | None] = mapped_column(String(100), comment="型号规格", nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, comment="数量", default=1)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态：0-维修，1-正常")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否删除")

    # 关联关系仅通过 ORM 维护，不建数据库层外键
    lab: Mapped["Lab"] = relationship(
        "Lab",
        backref="equipments",
        foreign_keys=[lab_id],
        primaryjoin="Equipment.lab_id == Lab.id",
    )

    @property
    def lab_name(self) -> str | None:
        return self.lab.name if self.lab else None

    def __repr__(self):
        return f"<Equipment(id={self.id}, name='{self.name}', lab_id={self.lab_id})>"
