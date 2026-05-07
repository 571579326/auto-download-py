from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdBrowserPage(Base):
    __tablename__ = 'ad_browser_page'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    window_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('ad_browser_window.id'), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(1), nullable=False, default='1')
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    invalid_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
