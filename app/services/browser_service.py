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
    SeleniumOpenWindowResponse,
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

    def open_browser_pure(self, url: str | None = None, new_window: bool | None = None) -> OpenWindowResponse:
        """纯净模式打开浏览器。

        不复用 browser-service 单线程队列，不挂接 Playwright，不调用 CDP HTTP，
        只按快捷方式等价命令启动 Chrome，避免 Cloudflare 保护页面受到自动化接管影响。
        """
        db = SessionLocal()
        try:
            return browser_session_manager.open_window_pure(db, url=url, new_window=new_window)
        finally:
            db.close()

    def open_browser_selenium(
        self,
        url: str | None = None,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> SeleniumOpenWindowResponse:
        """Selenium 短接管模式打开浏览器窗口。

        先确保 chromeTest/Chrome 以 remote-debugging-port 方式运行，
        再通过 Selenium debuggerAddress 附加、打开一个窗口或当前页，最后立刻 driver.quit() 断开。
        不保存全局 driver，不进入 browser-service 单线程队列。
        """
        db = SessionLocal()
        try:
            return browser_session_manager.open_window_selenium(
                db,
                url=url,
                new_window=new_window,
                ensure_browser=ensure_browser,
            )
        finally:
            db.close()

    def list_windows(self) -> WindowListResponse:
        return self._execute(browser_session_manager.list_windows)

    def new_tab(self, window_id: str, request: NewTabRequest | None = None) -> PageInfoResponse:
        return self._execute(browser_session_manager.new_tab, window_id, request)

    def open_url(self, window_id: str, request: OpenUrlRequest) -> PageInfoResponse:
        return self._execute(browser_session_manager.open_url, window_id, request)

    def open_config_pages(self, window_id: str, request: OpenConfiguredPagesRequest) -> BatchOpenPagesResponse:
        return self._execute(browser_session_manager.open_config_pages, window_id, request)

    def open_config_pages_selenium_once(
        self,
        config_code: str,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> BatchOpenPagesResponse:
        """Selenium 短接管打开配置页面。

        不复用全局 Playwright runtime，不进入 browser-service 单线程队列，
        打开完成后 Selenium driver 立即断开。
        """
        db = SessionLocal()
        try:
            return browser_session_manager.open_config_pages_selenium_once(
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
        """Playwright 短接管打开配置页面。

        用于替代 page-flow 旧的长期 Playwright/CDP 接管流程。
        """
        db = SessionLocal()
        try:
            return browser_session_manager.open_config_pages_playwright_once(
                db,
                config_code=config_code,
                new_window=new_window,
                ensure_browser=ensure_browser,
            )
        finally:
            db.close()

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
