from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdBrowserWindow(Base):
    __tablename__ = 'ad_browser_window'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    window_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(1), nullable=False, default='1')
    last_page_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    invalid_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
