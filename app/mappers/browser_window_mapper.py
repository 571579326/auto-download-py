from datetime import datetime

from sqlalchemy.orm import Session

from app.models.browser_page import AdBrowserPage
from app.models.browser_window import AdBrowserWindow


class BrowserWindowMapper:

    @staticmethod
    def create(db: Session, window_id: str) -> AdBrowserWindow:
        row = AdBrowserWindow(window_id=window_id, status='1')
        db.add(row)
        db.commit()
        return row

    @staticmethod
    def get_by_window_id(db: Session, window_id: str) -> AdBrowserWindow | None:
        return db.query(AdBrowserWindow).filter(AdBrowserWindow.window_id == window_id).one_or_none()

    @staticmethod
    def list_active(db: Session) -> list[AdBrowserWindow]:
        return (
            db.query(AdBrowserWindow)
            .filter(AdBrowserWindow.status == '1')
            .order_by(AdBrowserWindow.id.asc())
            .all()
        )

    @staticmethod
    def update_last_page_info(
        db: Session,
        db_window: AdBrowserWindow,
        title: str | None,
        url: str | None,
    ) -> None:
        db_window.last_page_title = title[:255] if title else None
        db_window.last_page_url = url[:500] if url else None
        db.commit()

    @staticmethod
    def invalidate_window_and_pages(db: Session, db_window: AdBrowserWindow) -> None:
        now = datetime.now()
        page_rows = (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == db_window.id, AdBrowserPage.status.in_(['0', '1']))
            .all()
        )
        for page_row in page_rows:
            page_row.status = '2'
            page_row.invalid_time = now
        db_window.status = '0'
        db_window.invalid_time = now
        db_window.last_page_title = None
        db_window.last_page_url = None
        db.commit()

    @staticmethod
    def invalidate_by_row_id(db: Session, window_row_id: int) -> None:
        db_window = db.query(AdBrowserWindow).filter(AdBrowserWindow.id == window_row_id).one_or_none()
        if db_window is None:
            return
        now = datetime.now()
        db_window.status = '0'
        db_window.invalid_time = now
        page_rows = db.query(AdBrowserPage).filter(AdBrowserPage.window_id == window_row_id).all()
        for row in page_rows:
            row.status = '2'
            row.invalid_time = now
        db.commit()


browser_window_mapper = BrowserWindowMapper()
