from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdBrowserPageConfig(Base):
    __tablename__ = 'ad_browser_page_config'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    config_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(1), nullable=False, default='1', index=True)
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    invalid_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
