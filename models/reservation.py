from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, Text
from models.base import Base


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = {"comment": "预约信息"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, comment="预约人", nullable=False, index=True
    )
    lab_id: Mapped[int] = mapped_column(
        Integer, comment="实验室", nullable=False, index=True
    )
    equipment_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment="设备，空表示预约实验室", nullable=True, index=True
    )
    date: Mapped[str] = mapped_column(String(20), comment="预约日期", nullable=False)
    start_time: Mapped[str] = mapped_column(
        String(20), comment="开始时间", nullable=False
    )
    end_time: Mapped[str] = mapped_column(
        String(20), comment="结束时间", nullable=False
    )
    remark: Mapped[Optional[str]] = mapped_column(
        String(255), comment="备注", nullable=True
    )
    status: Mapped[int] = mapped_column(
        Integer, comment="预约状态 0 待审核，1 已通过，2 已拒绝，3 已取消", default=0
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否删除"
    )

    # 关联关系仅通过 ORM 维护，不建数据库层外键
    user: Mapped[Optional["User"]] = relationship(
        "User",
        backref="reservations",
        foreign_keys=[user_id],
        primaryjoin="Reservation.user_id == User.id",
    )
    lab: Mapped["Lab"] = relationship(
        "Lab",
        backref="reservations",
        foreign_keys=[lab_id],
        primaryjoin="Reservation.lab_id == Lab.id",
    )
    equipment: Mapped[Optional["Equipment"]] = relationship(
        "Equipment",
        backref="reservations",
        foreign_keys=[equipment_id],
        primaryjoin="Reservation.equipment_id == Equipment.id",
    )

    @property
    def user_name(self) -> Optional[str]:
        return self.user.username if self.user else None

    @property
    def lab_name(self) -> Optional[str]:
        return self.lab.name if self.lab else None

    @property
    def equipment_name(self) -> Optional[str]:
        return self.equipment.name if self.equipment else None

    def __repr__(self):
        return f"<Reservation(id={self.id}, user_id={self.user_id}, lab_id={self.lab_id}, date='{self.date}', status={self.status})>"