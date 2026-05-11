from datetime import datetime

from sqlalchemy.orm import Session

from app.models.browser_page import AdBrowserPage


class BrowserPageMapper:

    @staticmethod
    def create(
        db: Session,
        window_row_id: int,
        title: str | None,
        url: str | None,
        status: str,
        sort_no: int,
    ) -> AdBrowserPage:
        row = AdBrowserPage(
            window_id=window_row_id,
            title=title[:255] if title else None,
            url=url[:1000] if url else None,
            status=status,
            sort_no=sort_no,
        )
        db.add(row)
        db.commit()
        return row

    @staticmethod
    def get_valid_pages(db: Session, window_row_id: int) -> list[AdBrowserPage]:
        return (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status.in_(['0', '1']))
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .all()
        )

    @staticmethod
    def get_active_page(db: Session, window_row_id: int) -> AdBrowserPage | None:
        return (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status == '1')
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .one_or_none()
        )

    @staticmethod
    def get_by_id(db: Session, page_db_id: int) -> AdBrowserPage | None:
        return db.query(AdBrowserPage).filter(AdBrowserPage.id == page_db_id).one_or_none()

    @staticmethod
    def next_sort_no(db: Session, window_row_id: int) -> int:
        rows = (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id)
            .order_by(AdBrowserPage.sort_no.desc(), AdBrowserPage.id.desc())
            .limit(1)
            .all()
        )
        if not rows:
            return 1
        return rows[0].sort_no + 1

    @staticmethod
    def set_active_status(db: Session, window_row_id: int, active_page_db_id: int | None) -> list[AdBrowserPage]:
        page_rows = (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status.in_(['0', '1']))
            .all()
        )
        for row in page_rows:
            row.status = '1' if active_page_db_id is not None and row.id == active_page_db_id else '0'
        db.commit()
        return page_rows

    @staticmethod
    def invalidate_page(db: Session, page_db_id: int) -> None:
        page_row = db.query(AdBrowserPage).filter(AdBrowserPage.id == page_db_id).one_or_none()
        if page_row is None or page_row.status == '2':
            return
        page_row.status = '2'
        page_row.invalid_time = datetime.now()
        db.commit()

    @staticmethod
    def sync_snapshot(
        db: Session,
        page_row: AdBrowserPage,
        title: str | None,
        url: str | None,
        auto_commit: bool = True,
    ) -> None:
        page_row.title = title[:255] if title else None
        page_row.url = url[:1000] if url else None
        if auto_commit:
            db.commit()

    @staticmethod
    def get_source_pages_for_reopen(db: Session, window_row_id: int) -> list[AdBrowserPage]:
        return (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status.in_(['0', '1']))
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .all()
        )


browser_page_mapper = BrowserPageMapper()
