from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from app.browser.manager import browser_session_manager
from app.db.session import SessionLocal
from app.schemas.browser import (
    BatchOpenPagesResponse,
    BingHuyaRequest,
    ClosePageResponse,
    InvalidateWindowResponse,
    NewTabRequest,
    OpenConfiguredPagesRequest,
    OpenUrlRequest,
    OpenWindowResponse,
    PageInfoResponse,
    PageListResponse,
    ReopenWindowResponse,
    WindowListResponse,
)

T = TypeVar('T')


class BrowserService:
    """给本地业务代码直接调用的浏览器服务层。"""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='browser-service')

    def _execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        def job() -> T:
            db = SessionLocal()
            try:
                return func(db, *args, **kwargs)
            finally:
                db.close()

        future = self._executor.submit(job)
        return future.result()

    def open_browser(self) -> OpenWindowResponse:
        return self._execute(browser_session_manager.open_window)

    def list_windows(self) -> WindowListResponse:
        return self._execute(browser_session_manager.list_windows)

    def new_tab(self, window_id: str, request: NewTabRequest | None = None) -> PageInfoResponse:
        return self._execute(browser_session_manager.new_tab, window_id, request)

    def open_url(self, window_id: str, request: OpenUrlRequest) -> PageInfoResponse:
        return self._execute(browser_session_manager.open_url, window_id, request)

    def open_config_pages(self, window_id: str, request: OpenConfiguredPagesRequest) -> BatchOpenPagesResponse:
        return self._execute(browser_session_manager.open_config_pages, window_id, request)

    def list_pages(self, window_id: str) -> PageListResponse:
        return self._execute(browser_session_manager.list_pages, window_id)

    def get_page_info(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_session_manager.get_page_info, window_id, page_id, url_contains)

    def takeover_page_info(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_session_manager.takeover_latest_page_info, window_id, page_id, url_contains)

    def activate_page(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_session_manager.activate_page, window_id, page_id, url_contains)

    def close_page(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> ClosePageResponse:
        return self._execute(browser_session_manager.close_page, window_id, page_id, url_contains)

    def bing_huya(self, window_id: str, request: BingHuyaRequest | None = None) -> PageInfoResponse:
        return self._execute(browser_session_manager.bing_huya, window_id, request)

    def reopen_window(self, window_id: str) -> ReopenWindowResponse:
        return self._execute(browser_session_manager.reopen_window, window_id)

    def invalidate_window(self, window_id: str) -> InvalidateWindowResponse:
        return self._execute(browser_session_manager.invalidate_window, window_id)

    def close_browser(self, window_id: str) -> InvalidateWindowResponse:
        return self._execute(browser_session_manager.invalidate_window, window_id)


browser_service = BrowserService()
