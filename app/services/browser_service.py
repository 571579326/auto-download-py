from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from app.db.session import SessionLocal
from app.services.browser_manager import browser_runtime_manager
from app.browser.rpa_locator_backend import rpa_locator_backend

from app.schemas.rpa import (
    RpaElementAttributeRequest,
    RpaElementClickRequest,
    RpaElementInputRequest,
    RpaElementOperationResponse,
    RpaElementPressRequest,
    RpaElementSelectRequest,
    RpaElementTextRequest,
    RpaLocatorCountRequest,
    RpaLocatorCountResponse,
    RpaLocatorDescribeRequest,
    RpaLocatorFindRequest,
    RpaLocatorFindResponse,
    RpaPageReloadRequest,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaScreenshotRequest,
    RpaScreenshotResponse,
)
from app.schemas.browser import (
    BatchOpenPagesResponse,
    BingHuyaRequest,
    ClosePageResponse,
    InvalidateWindowResponse,
    NewTabRequest,
    OpenConfiguredPagesRequest,
    OpenUrlRequest,
    OpenWindowResponse,
    SeleniumOpenWindowResponse,
    PageInfoResponse,
    PageListResponse,
    ReopenWindowResponse,
    WindowListResponse,
)

T = TypeVar('T')


class BrowserService:

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
        return self._execute(browser_runtime_manager.open_window)

    def open_browser_pure(self, url: str | None = None, new_window: bool | None = None) -> OpenWindowResponse:
        db = SessionLocal()
        try:
            return browser_runtime_manager.open_window_pure(db, url=url, new_window=new_window)
        finally:
            db.close()

    def open_browser_selenium(
        self,
        url: str | None = None,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> SeleniumOpenWindowResponse:
        db = SessionLocal()
        try:
            return browser_runtime_manager.open_window_selenium(
                db,
                url=url,
                new_window=new_window,
                ensure_browser=ensure_browser,
            )
        finally:
            db.close()

    def list_windows(self) -> WindowListResponse:
        return self._execute(browser_runtime_manager.list_windows)

    def new_tab(self, window_id: str, request: NewTabRequest | None = None) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.new_tab, window_id, request)

    def open_url(self, window_id: str, request: OpenUrlRequest) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.open_url, window_id, request)

    def open_config_pages(self, window_id: str, request: OpenConfiguredPagesRequest) -> BatchOpenPagesResponse:
        return self._execute(browser_runtime_manager.open_config_pages, window_id, request)

    def open_config_pages_selenium_once(
        self,
        config_code: str,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> BatchOpenPagesResponse:
        db = SessionLocal()
        try:
            return browser_runtime_manager.open_config_pages_selenium_once(
                db,
                config_code=config_code,
                new_window=new_window,
                ensure_browser=ensure_browser,
            )
        finally:
            db.close()

    def open_config_pages_playwright_once(
        self,
        config_code: str,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> BatchOpenPagesResponse:
        db = SessionLocal()
        try:
            return browser_runtime_manager.open_config_pages_playwright_once(
                db,
                config_code=config_code,
                new_window=new_window,
                ensure_browser=ensure_browser,
            )
        finally:
            db.close()

    def list_pages(self, window_id: str) -> PageListResponse:
        return self._execute(browser_runtime_manager.list_pages, window_id)

    def get_page_info(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.get_page_info, window_id, page_id, url_contains)

    def takeover_page_info(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.takeover_latest_page_info, window_id, page_id, url_contains)

    def activate_page(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.activate_page, window_id, page_id, url_contains)

    def close_page(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> ClosePageResponse:
        return self._execute(browser_runtime_manager.close_page, window_id, page_id, url_contains)

    def bing_huya(self, window_id: str, request: BingHuyaRequest | None = None) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.bing_huya, window_id, request)

    def reopen_window(self, window_id: str) -> ReopenWindowResponse:
        return self._execute(browser_runtime_manager.reopen_window, window_id)

    def invalidate_window(self, window_id: str) -> InvalidateWindowResponse:
        return self._execute(browser_runtime_manager.invalidate_window, window_id)

    # ----------------------------- RPA common actions -----------------------------
    def rpa_reconnect_page(
        self,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.rpa_reconnect_page, window_id, page_id, url_contains)

    def rpa_reload_page(self, request: RpaPageReloadRequest) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.rpa_reload_page, request)

    def rpa_wait_load_state(self, request: RpaPageWaitLoadStateRequest) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.rpa_wait_load_state, request)

    def rpa_wait_url_contains(self, request: RpaPageWaitUrlRequest) -> PageInfoResponse:
        return self._execute(browser_runtime_manager.rpa_wait_url_contains, request)

    def rpa_screenshot(self, request: RpaScreenshotRequest) -> RpaScreenshotResponse:
        return self._execute(browser_runtime_manager.rpa_screenshot, request)

    def rpa_element_exists(self, request: RpaElementTextRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_exists, request)

    def rpa_element_click(self, request: RpaElementClickRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_click, request)

    def rpa_element_input(self, request: RpaElementInputRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_input, request)

    def rpa_element_text(self, request: RpaElementTextRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_text, request)

    def rpa_element_attribute(self, request: RpaElementAttributeRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_attribute, request)

    def rpa_element_press(self, request: RpaElementPressRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_press, request)

    def rpa_element_select(self, request: RpaElementSelectRequest) -> RpaElementOperationResponse:
        return self._execute(browser_runtime_manager.rpa_element_select, request)


    def rpa_locator_find(self, request: RpaLocatorFindRequest) -> RpaLocatorFindResponse:
        return self._execute(rpa_locator_backend.find, request)

    def rpa_locator_describe(self, request: RpaLocatorDescribeRequest) -> RpaLocatorFindResponse:
        return self._execute(rpa_locator_backend.describe, request)

    def rpa_locator_count(self, request: RpaLocatorCountRequest) -> RpaLocatorCountResponse:
        return self._execute(rpa_locator_backend.count, request)

    def close_browser(self, window_id: str) -> InvalidateWindowResponse:
        return self._execute(browser_runtime_manager.invalidate_window, window_id)


browser_service = BrowserService()
