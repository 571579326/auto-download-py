import asyncio
import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from playwright.sync_api import Browser, BrowserContext, CDPSession, Error, Page, Playwright, sync_playwright
from sqlalchemy.orm import Session

from app.core.asyncio_policy import ensure_windows_proactor_event_loop_policy
from app.core.config import get_settings
from app.models.browser_page import AdBrowserPage
from app.models.browser_page_config import AdBrowserPageConfig
from app.models.browser_window import AdBrowserWindow
from app.schemas.browser import (
    BatchOpenPageItem,
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
    PageSummary,
    ReopenWindowResponse,
    WindowListResponse,
    WindowSummary,
)

from app.schemas.rpa import (
    RpaPageReloadRequest,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaScreenshotRequest,
    RpaScreenshotResponse,
)
from app.utils.http_utils import get_json, put_json
from app.utils.port_utils import is_port_open

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class BrowserRuntime:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    browser_cdp: CDPSession
    lock: threading.RLock


@dataclass
class WindowRuntime:
    lock: threading.RLock = field(default_factory=threading.RLock)
    page_map: dict[int, Page] = field(default_factory=dict)
    active_page_db_id: int | None = None
    root_page_db_id: int | None = None


class BrowserSessionManager:
    def __init__(self) -> None:
        self._browser_runtime: BrowserRuntime | None = None
        self._window_runtime_map: dict[str, WindowRuntime] = {}
        self._global_lock = threading.RLock()

    def _log_event_loop_policy(self, stage: str) -> None:
        logger.info(
            'event loop policy检查, stage=%s, policy=%s',
            stage,
            asyncio.get_event_loop_policy().__class__.__name__,
        )

    # ----------------------------- public api -----------------------------
    def open_window(self, db: Session) -> OpenWindowResponse:
        self._ensure_profile_dir()
        self._ensure_browser_executable_path()

        window_id = uuid.uuid4().hex
        db_window = AdBrowserWindow(window_id=window_id, status='1')
        db.add(db_window)
        db.commit()

        try:
            browser_runtime, launched_now = self._ensure_browser_runtime_with_state()

            if self._is_cdp_http_open_page_mode():
                start_url = settings.start_url or 'about:blank'
                page_title = ''
                page_url = start_url
                # 如果是已有调试端口，明确创建一个新 target，避免关闭窗口后再次 open 没有可见窗口。
                # 如果是本次刚启动，Chrome 进程命令行已打开 start_url，不再额外打开第二个空白页。
                if not launched_now:
                    try:
                        target_payload = self._open_url_by_cdp_http(start_url)
                        page_title = str(target_payload.get('title') or '')
                        page_url = str(target_payload.get('url') or start_url)
                    except Exception as exc:
                        logger.warning('CDP HTTP 创建 session root target 失败，继续返回会话, url=%s, msg=%s', start_url, exc)

                page_row = self._create_page_record(
                    db=db,
                    window_row_id=db_window.id,
                    title=page_title,
                    url=page_url,
                    status='1',
                    sort_no=1,
                )
                self._window_runtime_map[window_id] = WindowRuntime(
                    page_map={},
                    active_page_db_id=page_row.id,
                    root_page_db_id=page_row.id,
                )
                self._update_window_last_page_info(db, db_window, page_row.title, page_row.url)
                logger.info(
                    '打开窗口成功(CDP_HTTP轻量模式), windowId=%s, rootPageId=%s, launchedNow=%s',
                    window_id,
                    page_row.id,
                    launched_now,
                )
                return OpenWindowResponse(
                    windowId=window_id,
                    sessionId=window_id,
                    status='1',
                    userDataDir=settings.profile_dir,
                    debugPort=settings.debug_port,
                )

            page = self._acquire_window_root_page(browser_runtime, launched_now, settings.start_url or 'about:blank')
            page_row = self._create_page_record(
                db=db,
                window_row_id=db_window.id,
                title=self._safe_title(page),
                url=self._safe_url(page),
                status='1',
                sort_no=1,
            )
            self._window_runtime_map[window_id] = WindowRuntime(
                page_map={page_row.id: page},
                active_page_db_id=page_row.id,
                root_page_db_id=page_row.id,
            )
            self._update_window_last_page_info(db, db_window, page_row.title, page_row.url)
            logger.info('打开窗口成功, windowId=%s, rootPageId=%s, launchedNow=%s', window_id, page_row.id, launched_now)
            return OpenWindowResponse(
                windowId=window_id,
                sessionId=window_id,
                status='1',
                userDataDir=settings.profile_dir,
                debugPort=settings.debug_port,
            )
        except Exception as exc:
            logger.exception('open_window失败, windowId=%s, msg=%s', window_id, exc)
            self._window_runtime_map.pop(window_id, None)
            self._invalidate_window_rows(db, db_window.id)
            raise RuntimeError(f'打开浏览器窗口失败: {exc.__class__.__name__}: {exc}') from exc

    def open_window_pure(
        self,
        db: Session,
        url: str | None = None,
        new_window: bool | None = None,
    ) -> OpenWindowResponse:
        """纯净模式打开浏览器。

        该方法专门用于 Cloudflare 等对自动化接管敏感的网站：
        - 不调用 Playwright connect_over_cdp；
        - 不调用 /json/new；
        - 不读取 page/title/iframe/target；
        - 不进入 browser-service 单线程队列；
        - 只用与手动快捷方式尽量一致的 Chrome 命令启动浏览器。
        """
        self._ensure_profile_dir()
        self._ensure_browser_executable_path()

        window_id = uuid.uuid4().hex
        db_window = AdBrowserWindow(window_id=window_id, status='1')
        db.add(db_window)
        db.commit()

        safe_url = (url or settings.pure_browser_start_url or '').strip()
        use_new_window = settings.pure_browser_new_window if new_window is None else bool(new_window)

        try:
            browser_process = self._launch_browser_pure_process(safe_url, use_new_window)
            page_url = safe_url or ''
            page_row = self._create_page_record(
                db=db,
                window_row_id=db_window.id,
                title='',
                url=page_url,
                status='1',
                sort_no=1,
            )
            self._update_window_last_page_info(db, db_window, '', page_url)
            logger.info(
                '纯净模式打开浏览器成功, windowId=%s, pid=%s, url=%s, newWindow=%s, profileDir=%s, debugPort=%s',
                window_id,
                browser_process.pid,
                safe_url or '<default>',
                use_new_window,
                settings.profile_dir,
                settings.debug_port,
            )
            return OpenWindowResponse(
                windowId=window_id,
                sessionId=window_id,
                status='1',
                userDataDir=settings.profile_dir,
                debugPort=settings.debug_port,
            )
        except Exception as exc:
            logger.exception('open_window_pure失败, windowId=%s, msg=%s', window_id, exc)
            self._invalidate_window_rows(db, db_window.id)
            raise RuntimeError(f'纯净模式打开浏览器失败: {exc.__class__.__name__}: {exc}') from exc

    def open_window_selenium(
        self,
        db: Session,
        url: str | None = None,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> SeleniumOpenWindowResponse:
        """Selenium 附加模式打开浏览器窗口。

        设计目标：
        - 先保证 chromeTest/Chrome 是用 remote-debugging-port + 独立 profile 启动；
        - 再用 Selenium debuggerAddress 短暂附加；
        - 打开目标 URL 后立即 driver.quit() 断开；
        - 不保存全局 driver，避免长期自动化接管。
        """
        self._ensure_profile_dir()
        self._ensure_browser_executable_path()

        window_id = uuid.uuid4().hex
        db_window = AdBrowserWindow(window_id=window_id, status='1')
        db.add(db_window)
        db.commit()

        safe_url = (url or settings.selenium_browser_start_url or 'about:blank').strip()
        use_new_window = settings.selenium_browser_new_window if new_window is None else bool(new_window)
        browser_started_now = False
        driver_detached = False
        title = ''
        opened_url = safe_url

        try:
            if not is_port_open('127.0.0.1', settings.debug_port):
                if not ensure_browser:
                    raise RuntimeError(f'Chrome调试端口未启动: 127.0.0.1:{settings.debug_port}')
                browser_process = self._launch_browser_pure_process('', False)
                browser_started_now = True
                self._wait_for_cdp_ready(browser_process)

            driver = None
            try:
                driver = self._create_selenium_driver()
                page_load_timeout = max(settings.selenium_page_load_timeout_ms / 1000, 1)
                try:
                    driver.set_page_load_timeout(page_load_timeout)
                except Exception as exc:
                    logger.warning('Selenium设置页面加载超时失败，继续执行, msg=%s', exc)

                if use_new_window:
                    driver.switch_to.new_window('window')

                # 使用 location.href 发起跳转，避免 driver.get 在 Cloudflare/iframe 场景长期阻塞。
                if safe_url:
                    try:
                        driver.execute_script('window.location.href = arguments[0];', safe_url)
                    except Exception as exc:
                        logger.warning('Selenium execute_script跳转失败，尝试 driver.get, url=%s, msg=%s', safe_url, exc)
                        try:
                            driver.get(safe_url)
                        except Exception as get_exc:
                            logger.warning('Selenium driver.get未正常完成，浏览器可能已经开始加载，继续返回, url=%s, msg=%s', safe_url, get_exc)

                time.sleep(0.2)
                if settings.selenium_read_page_info:
                    try:
                        opened_url = driver.current_url or safe_url
                    except Exception:
                        opened_url = safe_url
                    try:
                        title = driver.title or ''
                    except Exception:
                        title = ''
                else:
                    opened_url = safe_url
                    title = ''
            finally:
                if driver is not None:
                    try:
                        driver.quit()
                        driver_detached = True
                    except Exception as exc:
                        logger.warning('Selenium driver.quit失败，继续返回, msg=%s', exc)

            self._create_page_record(
                db=db,
                window_row_id=db_window.id,
                title=title,
                url=opened_url,
                status='1',
                sort_no=1,
            )
            self._update_window_last_page_info(db, db_window, title, opened_url)
            logger.info(
                'Selenium附加模式打开窗口成功, windowId=%s, url=%s, title=%s, newWindow=%s, browserStartedNow=%s, driverDetached=%s',
                window_id,
                opened_url,
                title,
                use_new_window,
                browser_started_now,
                driver_detached,
            )
            return SeleniumOpenWindowResponse(
                windowId=window_id,
                sessionId=window_id,
                status='1',
                userDataDir=settings.profile_dir,
                debugPort=settings.debug_port,
                url=opened_url,
                title=title,
                newWindow=use_new_window,
                browserStartedNow=browser_started_now,
                driverDetached=driver_detached,
                message='Selenium已附加到现有Chrome，打开URL后已断开driver。',
            )
        except Exception as exc:
            logger.exception('open_window_selenium失败, windowId=%s, msg=%s', window_id, exc)
            self._invalidate_window_rows(db, db_window.id)
            raise RuntimeError(f'Selenium附加模式打开浏览器窗口失败: {exc.__class__.__name__}: {exc}') from exc

    def open_config_pages_selenium_once(
        self,
        db: Session,
        config_code: str,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> BatchOpenPagesResponse:
        """用 Selenium 短接管方式复现 page-flow 的打开配置页步骤。

        该方法不依赖全局 Playwright runtime，不进入长期接管：
        - 如 9222 未启动，先用纯净模式启动 Chrome；
        - Selenium 通过 debuggerAddress 附加到已有 Chrome；
        - 按 configCode 打开配置 URL；
        - 立即 driver.quit() 断开；
        - 仅记录数据库快照，后续图像点击仍走桌面截图。
        """
        return self._open_config_pages_by_selenium_once(
            db=db,
            config_code=config_code,
            new_window=new_window,
            ensure_browser=ensure_browser,
        )

    def open_config_pages_playwright_once(
        self,
        db: Session,
        config_code: str,
        new_window: bool | None = None,
        ensure_browser: bool = True,
    ) -> BatchOpenPagesResponse:
        """用 Playwright 短接管方式打开配置页。

        这是原 page-flow 的低强度 Playwright 版本：
        - 不调用 open_window，不创建全局 BrowserRuntime；
        - 不做 Chrome diagnostics / extension diagnostics；
        - 不等待 DOMContentLoaded / iframe / load；
        - 连接 CDP 后只执行打开 URL 的必要动作，然后立刻停止 Playwright。
        """
        return self._open_config_pages_by_playwright_once(
            db=db,
            config_code=config_code,
            new_window=new_window,
            ensure_browser=ensure_browser,
        )

    def list_windows(self, db: Session) -> WindowListResponse:
        rows = (
            db.query(AdBrowserWindow)
            .filter(AdBrowserWindow.status == '1')
            .order_by(AdBrowserWindow.id.asc())
            .all()
        )
        windows = [
            WindowSummary(
                windowId=row.window_id,
                status=row.status,
                lastPageTitle=row.last_page_title,
                lastPageUrl=row.last_page_url,
                createdTime=row.created_time,
                updatedTime=row.updated_time,
            )
            for row in rows
        ]
        return WindowListResponse(total=len(windows), windows=windows)

    def new_tab(self, db: Session, window_id: str, request: Optional[NewTabRequest]) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        req = request or NewTabRequest()
        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                page_row = self._create_cdp_http_page_record(
                    db=db,
                    db_window=db_window,
                    url=req.url,
                    status='1' if req.bringToFront else '0',
                    sort_no=self._next_sort_no(db, db_window.id),
                )
                if req.bringToFront:
                    self._set_active_page(db, db_window, runtime, page_row.id)
                else:
                    self._update_window_last_page_info(db, db_window, page_row.title, page_row.url)
                return self._build_page_info_response(db, db_window, runtime, page_row)

            page_row, _ = self._create_managed_page_in_window(
                db=db,
                db_window=db_window,
                window_runtime=runtime,
                url=req.url,
                active=req.bringToFront,
            )
            if not req.bringToFront:
                self._sync_active_status_from_runtime(db, db_window, runtime)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def open_url(self, db: Session, window_id: str, request: OpenUrlRequest) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                if request.newTab:
                    page_row = self._create_cdp_http_page_record(
                        db=db,
                        db_window=db_window,
                        url=request.url,
                        status='1' if request.bringToFront else '0',
                        sort_no=self._next_sort_no(db, db_window.id),
                    )
                else:
                    page_row = self._resolve_cdp_http_page_row(db, db_window, request.pageId, request.urlContains)
                    target_payload = self._open_url_by_cdp_http(request.url)
                    page_row.title = str(target_payload.get('title') or '')[:255] or None
                    page_url = str(target_payload.get('url') or request.url)
                    page_row.url = page_url[:1000] if page_url else None
                    db.commit()
                if request.bringToFront:
                    self._set_active_page(db, db_window, runtime, page_row.id)
                else:
                    self._update_window_last_page_info(db, db_window, page_row.title, page_row.url)
                return self._build_page_info_response(db, db_window, runtime, page_row)

            if request.newTab:
                page_row, page = self._create_managed_page_in_window(
                    db=db,
                    db_window=db_window,
                    window_runtime=runtime,
                    url=request.url,
                    active=request.bringToFront,
                )
                if not request.bringToFront:
                    self._sync_page_snapshot(db, page_row, page)
                    self._sync_active_status_from_runtime(db, db_window, runtime)
                return self._build_page_info_response(db, db_window, runtime, page_row)

            page_row, page = self._resolve_managed_page(db, db_window, runtime, request.pageId, request.urlContains)
            page.goto(request.url, wait_until='domcontentloaded', timeout=settings.start_timeout_ms)
            self._sync_page_snapshot(db, page_row, page)
            if request.bringToFront:
                page.bring_to_front()
                self._set_active_page(db, db_window, runtime, page_row.id)
            else:
                self._sync_active_status_from_runtime(db, db_window, runtime)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def open_config_pages(
        self,
        db: Session,
        window_id: str,
        request: OpenConfiguredPagesRequest,
    ) -> BatchOpenPagesResponse:
        config_code = (request.configCode or '').strip()
        if not config_code:
            raise ValueError('configCode cannot be empty')

        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        config_rows = self._select_valid_page_config_rows(db, config_code)
        if not config_rows:
            raise ValueError(f'no valid page config found: configCode={config_code}')

        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                opened_rows: list[AdBrowserPage] = []
                sort_no = self._next_sort_no(db, db_window.id)
                for index, config_row in enumerate(config_rows):
                    active = request.bringToFront and index == len(config_rows) - 1
                    page_row = self._create_cdp_http_page_record(
                        db=db,
                        db_window=db_window,
                        url=config_row.url,
                        status='1' if active else '0',
                        sort_no=sort_no,
                    )
                    opened_rows.append(page_row)
                    sort_no += 1
                if request.bringToFront and opened_rows:
                    self._set_active_page(db, db_window, runtime, opened_rows[-1].id)
                elif opened_rows:
                    self._update_window_last_page_info(db, db_window, opened_rows[-1].title, opened_rows[-1].url)

                opened_pages = [
                    self._build_page_info_response(db, db_window, runtime, row)
                    for row in opened_rows
                ]
                logger.info(
                    'open_config_pages success(CDP_HTTP轻量模式), windowId=%s, configCode=%s, opened=%s',
                    window_id,
                    config_code,
                    len(opened_pages),
                )
                return BatchOpenPagesResponse(
                    windowId=window_id,
                    sessionId=window_id,
                    configCode=config_code,
                    total=len(opened_pages),
                    openedPages=opened_pages,
                )

            _, opener_page = self._resolve_anchor_page_for_window(db, db_window, runtime)
            items = [
                BatchOpenPageItem(
                    url=row.url,
                    active=request.bringToFront and index == len(config_rows) - 1,
                )
                for index, row in enumerate(config_rows)
            ]
            opened_rows = self._open_pages_batch_in_window(
                db=db,
                db_window=db_window,
                window_runtime=runtime,
                root_page=opener_page,
                items=items,
                start_sort_no=self._next_sort_no(db, db_window.id),
            )
            if request.bringToFront and opened_rows:
                self._set_active_page(db, db_window, runtime, opened_rows[-1].id)
            else:
                self._sync_active_status_from_runtime(db, db_window, runtime)

            opened_pages = [
                self._build_page_info_response(db, db_window, runtime, row)
                for row in opened_rows
            ]
            logger.info(
                'open_config_pages success, windowId=%s, configCode=%s, opened=%s',
                window_id,
                config_code,
                len(opened_pages),
            )
            return BatchOpenPagesResponse(
                windowId=window_id,
                sessionId=window_id,
                configCode=config_code,
                total=len(opened_pages),
                openedPages=opened_pages,
            )

    def list_pages(self, db: Session, window_id: str) -> PageListResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            self._sync_window_snapshots(db, db_window, runtime)
            page_rows = self._select_valid_page_rows(db, db_window.id)
            if not page_rows:
                raise RuntimeError('当前窗口下没有页面可用')
            active_row = next((row for row in page_rows if row.status == '1'), None)
            pages = [
                PageSummary(
                    pageId=self._page_id_by_db_id(row.id),
                    pageIndex=index,
                    title=row.title or '',
                    url=row.url or '',
                    status=row.status,
                    isActive=row.status == '1',
                )
                for index, row in enumerate(page_rows, start=1)
            ]
            active_index = None
            active_page_id = None
            if active_row is not None:
                active_index = next(index for index, row in enumerate(page_rows, start=1) if row.id == active_row.id)
                active_page_id = self._page_id_by_db_id(active_row.id)
            return PageListResponse(
                windowId=window_id,
                sessionId=window_id,
                total=len(page_rows),
                activePageId=active_page_id,
                activePageIndex=active_index,
                pages=pages,
            )

    def get_page_info(
        self,
        db: Session,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                page_row = self._resolve_cdp_http_page_row(db, db_window, page_id, url_contains)
                self._set_active_page(db, db_window, runtime, page_row.id)
                return self._build_page_info_response(db, db_window, runtime, page_row)

            page_row, page = self._resolve_managed_page(db, db_window, runtime, page_id, url_contains)
            self._sync_page_snapshot(db, page_row, page)
            self._set_active_page(db, db_window, runtime, page_row.id)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def activate_page(
        self,
        db: Session,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                page_row = self._resolve_cdp_http_page_row(db, db_window, page_id, url_contains)
                self._set_active_page(db, db_window, runtime, page_row.id)
                return self._build_page_info_response(db, db_window, runtime, page_row)

            page_row, page = self._resolve_managed_page(db, db_window, runtime, page_id, url_contains)
            page.bring_to_front()
            self._sync_page_snapshot(db, page_row, page)
            self._set_active_page(db, db_window, runtime, page_row.id)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def close_page(
        self,
        db: Session,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> ClosePageResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            if self._is_cdp_http_open_page_mode():
                page_row = self._resolve_cdp_http_page_row(db, db_window, page_id, url_contains)
                current_page_id = self._page_id_by_db_id(page_row.id)
                self._invalidate_page_local(db, db_window, runtime, page_row.id, close_page=False)
                remaining_rows = self._select_valid_page_rows(db, db_window.id)
                if remaining_rows:
                    next_row = next((row for row in remaining_rows if row.status == '1'), remaining_rows[-1])
                    self._set_active_page(db, db_window, runtime, next_row.id)
                else:
                    runtime.active_page_db_id = None
                    self._update_window_last_page_info(db, db_window, None, None)
                logger.info('关闭页面记录成功(CDP_HTTP轻量模式), windowId=%s, pageId=%s, remaining=%s', window_id, current_page_id, len(remaining_rows))
                return ClosePageResponse(
                    windowId=window_id,
                    sessionId=window_id,
                    pageId=current_page_id,
                    closed=True,
                    remainingPages=len(remaining_rows),
                )

            page_row, page = self._resolve_managed_page(db, db_window, runtime, page_id, url_contains)
            current_page_id = self._page_id_by_db_id(page_row.id)
            self._invalidate_page_local(db, db_window, runtime, page_row.id, close_page=True)
            remaining_rows = self._select_valid_page_rows(db, db_window.id)
            if remaining_rows:
                next_row = next((row for row in remaining_rows if row.status == '1'), remaining_rows[-1])
                self._set_active_page(db, db_window, runtime, next_row.id)
            else:
                runtime.active_page_db_id = None
                self._update_window_last_page_info(db, db_window, None, None)
            logger.info(
                '关闭页面成功, windowId=%s, pageId=%s, remaining=%s',
                window_id,
                current_page_id,
                len(remaining_rows),
            )
            return ClosePageResponse(
                windowId=window_id,
                sessionId=window_id,
                pageId=current_page_id,
                closed=True,
                remainingPages=len(remaining_rows),
            )

    def bing_huya(self, db: Session, window_id: str, request: Optional[BingHuyaRequest]) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        req = request or BingHuyaRequest()
        with runtime.lock:
            page_row, page = self._create_managed_page_in_window(
                db=db,
                db_window=db_window,
                window_runtime=runtime,
                url=settings.bing_url,
                active=True,
            )
            try:
                page.wait_for_load_state('domcontentloaded')
                page.locator('textarea[name="q"], input[name="q"]').first.fill(req.keyword)
                page.keyboard.press('Enter')
                page.wait_for_load_state('domcontentloaded')

                link_locator = page.locator(f'a[href^="{req.targetPrefix}"]').first
                link_locator.wait_for(timeout=10_000)
                href = link_locator.get_attribute('href')
                if not href:
                    raise RuntimeError(f'未找到可点击的目标链接, targetPrefix={req.targetPrefix}')

                target_row, target_page = self._create_managed_page_in_window(
                    db=db,
                    db_window=db_window,
                    window_runtime=runtime,
                    url=href,
                    active=True,
                )
                self._sync_page_snapshot(db, target_row, target_page)
                logger.info('bingHuya成功, windowId=%s, clickedHref=%s', window_id, href)
                return self._build_page_info_response(db, db_window, runtime, target_row)
            except Exception as exc:
                raise RuntimeError(f'Bing 搜索并打开虎牙链接失败: {exc}') from exc

    def takeover_latest_page_info(
        self,
        db: Session,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        runtime, db_window = self._get_valid_window_runtime(db, window_id)
        with runtime.lock:
            if page_id:
                page_row, page = self._resolve_managed_page(db, db_window, runtime, page_id, url_contains)
            else:
                page = self._resolve_takeover_page(runtime, url_contains)
                page_row = self._find_page_row_by_object(db, db_window, runtime, page)
                if page_row is None:
                    page_row = self._adopt_untracked_page(db, db_window, runtime, page)
            self._sync_page_snapshot(db, page_row, page)
            self._set_active_page(db, db_window, runtime, page_row.id)
            response = self._build_page_info_response(db, db_window, runtime, page_row)
            logger.info(
                'takeoverPageInfo成功, windowId=%s, pageId=%s, title=%s, url=%s',
                window_id,
                response.pageId,
                response.title,
                response.url,
            )
            return response

    # ----------------------------- RPA page helpers -----------------------------
    def _resolve_rpa_page(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> tuple[AdBrowserPage, Page]:
        """解析 RPA 操作目标页。"""
        if page_id:
            return self._resolve_managed_page(db, db_window, window_runtime, page_id, url_contains)
        try:
            return self._resolve_managed_page(db, db_window, window_runtime, None, url_contains)
        except Exception as managed_exc:
            logger.info(
                'RPA目标页未在已记录页面中命中，准备短接管浏览器页面, windowId=%s, urlContains=%s, reason=%s',
                db_window.window_id,
                url_contains,
                managed_exc,
            )
        page = self._resolve_takeover_page(window_runtime, url_contains)
        page_row = self._find_page_row_by_object(db, db_window, window_runtime, page)
        if page_row is None:
            page_row = self._adopt_untracked_page(db, db_window, window_runtime, page)
        return page_row, page

    def rpa_reconnect_page(
        self,
        db: Session,
        window_id: str,
        page_id: str | None = None,
        url_contains: str | None = None,
    ) -> PageInfoResponse:
        """RPA 公共动作：重连/接管页面并返回页面信息。"""
        return self.takeover_latest_page_info(db, window_id, page_id, url_contains)

    def rpa_reload_page(self, db: Session, request: RpaPageReloadRequest) -> PageInfoResponse:
        """RPA 公共动作：刷新目标页面。"""
        runtime, db_window = self._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = self._resolve_rpa_page(db, db_window, runtime, request.pageId, request.urlContains)
            page.reload(wait_until=request.waitUntil, timeout=request.timeoutMs)
            self._sync_page_snapshot(db, page_row, page)
            self._set_active_page(db, db_window, runtime, page_row.id)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def rpa_wait_load_state(self, db: Session, request: RpaPageWaitLoadStateRequest) -> PageInfoResponse:
        """RPA 公共动作：等待目标页面达到指定加载状态。"""
        runtime, db_window = self._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = self._resolve_rpa_page(db, db_window, runtime, request.pageId, request.urlContains)
            page.wait_for_load_state(request.state, timeout=request.timeoutMs)
            self._sync_page_snapshot(db, page_row, page)
            self._set_active_page(db, db_window, runtime, page_row.id)
            return self._build_page_info_response(db, db_window, runtime, page_row)

    def rpa_wait_url_contains(self, db: Session, request: RpaPageWaitUrlRequest) -> PageInfoResponse:
        """RPA 公共动作：等待当前 URL 包含指定关键字。"""
        runtime, db_window = self._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = self._resolve_rpa_page(db, db_window, runtime, request.pageId, request.urlContains)
            deadline = time.time() + request.timeoutMs / 1000
            while time.time() < deadline:
                current_url = self._safe_url(page)
                if request.urlContainsTarget in current_url:
                    self._sync_page_snapshot(db, page_row, page)
                    self._set_active_page(db, db_window, runtime, page_row.id)
                    return self._build_page_info_response(db, db_window, runtime, page_row)
                time.sleep(request.retryIntervalMs / 1000)
            raise RuntimeError(f'等待URL包含关键字超时: {request.urlContainsTarget}, current={self._safe_url(page)}')

    def rpa_screenshot(self, db: Session, request: RpaScreenshotRequest) -> RpaScreenshotResponse:
        """RPA 公共动作：对目标页面截图并保存到本地文件。"""
        runtime, db_window = self._get_valid_window_runtime(db, request.windowId)
        with runtime.lock:
            page_row, page = self._resolve_rpa_page(db, db_window, runtime, request.pageId, request.urlContains)
            if request.path and request.path.strip():
                output_path = Path(request.path.strip())
            else:
                output_dir = Path('screenshots')
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f'rpa_{request.windowId}_{page_row.id}_{int(time.time() * 1000)}.png'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output_path), full_page=request.fullPage)
            self._sync_page_snapshot(db, page_row, page)
            return RpaScreenshotResponse(
                success=True,
                path=str(output_path),
                windowId=request.windowId,
                pageId=self._page_id_by_db_id(page_row.id),
                title=page_row.title or '',
                url=page_row.url or '',
            )

    def reopen_window(self, db: Session, old_window_id: str) -> ReopenWindowResponse:
        old_window = self._select_window_by_window_id(db, old_window_id)
        if old_window is None:
            raise ValueError(f'windowId不存在: {old_window_id}')

        old_runtime = self._window_runtime_map.get(old_window_id)
        if old_runtime is not None:
            with old_runtime.lock:
                self._sync_window_snapshots(db, old_window, old_runtime)

        source_pages = (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == old_window.id, AdBrowserPage.status.in_(['0', '1']))
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .all()
        )
        if not source_pages:
            raise RuntimeError(f'windowId下没有可恢复的有效页面: {old_window_id}')

        self._ensure_profile_dir()
        self._ensure_browser_executable_path()
        browser_runtime = self._ensure_browser_runtime()

        new_window_id = uuid.uuid4().hex
        new_window = AdBrowserWindow(window_id=new_window_id, status='1')
        db.add(new_window)
        db.commit()

        old_runtime = self._window_runtime_map.get(old_window_id)
        restored_count = 0
        closed_old_window = False
        try:
            first_source = source_pages[0]
            first_page = self._create_new_browser_window_page(browser_runtime, first_source.url or 'about:blank')
            first_row = self._create_page_record(
                db=db,
                window_row_id=new_window.id,
                title=self._safe_title(first_page),
                url=self._safe_url(first_page),
                status='0',
                sort_no=1,
            )
            new_runtime = WindowRuntime(
                page_map={first_row.id: first_page},
                active_page_db_id=None,
                root_page_db_id=first_row.id,
            )
            self._window_runtime_map[new_window_id] = new_runtime
            restored_map: list[tuple[AdBrowserPage, AdBrowserPage]] = [(first_source, first_row)]
            restored_count = 1

            root_page = first_page
            batch_items = [
                BatchOpenPageItem(url=(row.url or 'about:blank'), active=False)
                for row in source_pages[1:]
            ]
            opened_rows = self._open_pages_batch_in_window(
                db=db,
                db_window=new_window,
                window_runtime=new_runtime,
                root_page=root_page,
                items=batch_items,
                start_sort_no=2,
            )
            restored_map.extend(list(zip(source_pages[1:], opened_rows)))
            restored_count = len(restored_map)

            active_source = next((row for row in source_pages if row.status == '1'), None)
            if active_source is None:
                active_row = restored_map[-1][1]
            else:
                active_row = next(target for source, target in restored_map if source.id == active_source.id)
            self._set_active_page(db, new_window, new_runtime, active_row.id)
            self._sync_window_snapshots(db, new_window, new_runtime)

            closed_old_window = self._invalidate_window_local(db, old_window_id, close_pages=True)
            logger.info(
                '重开窗口成功, oldWindowId=%s, newWindowId=%s, restoredPages=%s',
                old_window_id,
                new_window_id,
                restored_count,
            )
            return ReopenWindowResponse(
                oldWindowId=old_window_id,
                newWindowId=new_window_id,
                status='1',
                restoredPages=restored_count,
                closedOldWindow=closed_old_window,
            )
        except Exception as exc:
            logger.exception('reopen_window失败, oldWindowId=%s, newWindowId=%s, msg=%s', old_window_id, new_window_id, exc)
            self._window_runtime_map.pop(new_window_id, None)
            self._invalidate_window_rows(db, new_window.id)
            raise RuntimeError(f'重开窗口失败: {exc.__class__.__name__}: {exc}') from exc

    def invalidate_window(self, db: Session, window_id: str) -> InvalidateWindowResponse:
        closed = self._invalidate_window_local(db, window_id, close_pages=True)
        logger.info('失效窗口完成, windowId=%s, closed=%s', window_id, closed)
        return InvalidateWindowResponse(windowId=window_id, sessionId=window_id, status='0', closed=closed)

    def shutdown(self) -> None:
        with self._global_lock:
            self._window_runtime_map.clear()
            self._shutdown_browser_runtime()

    # ----------------------------- runtime helpers -----------------------------
    def _ensure_browser_runtime(self) -> BrowserRuntime:
        runtime, _ = self._ensure_browser_runtime_with_state()
        return runtime

    def _ensure_browser_runtime_with_state(self) -> tuple[BrowserRuntime, bool]:
        with self._global_lock:
            runtime = self._browser_runtime
            if runtime is not None and self._is_browser_runtime_alive(runtime):
                return runtime, False
            return self._rebuild_browser_runtime_locked()

    def _rebuild_browser_runtime(self) -> tuple[BrowserRuntime, bool]:
        with self._global_lock:
            return self._rebuild_browser_runtime_locked()

    def _rebuild_browser_runtime_locked(self) -> tuple[BrowserRuntime, bool]:
        self._shutdown_browser_runtime()
        if is_port_open('127.0.0.1', settings.debug_port):
            logger.info('检测到已存在浏览器调试端口，直接尝试重新挂接, debugPort=%s', settings.debug_port)
            try:
                return self._attach_browser_runtime(), False
            except Exception as exc:
                logger.warning('重新挂接已存在浏览器失败，准备重新拉起浏览器, debugPort=%s, msg=%s', settings.debug_port,
                               exc)
                self._shutdown_browser_runtime()

        browser_process = self._launch_browser_process()
        logger.info('浏览器进程已启动, pid=%s', browser_process.pid)
        self._wait_for_cdp_ready(browser_process)
        return self._attach_browser_runtime(), True

    def _attach_browser_runtime(self) -> BrowserRuntime:
        ensure_windows_proactor_event_loop_policy()
        self._log_event_loop_policy('before_sync_playwright_start')
        playwright = None
        browser = None
        browser_cdp = None
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.connect_over_cdp(
                self._build_cdp_url(),
                timeout=settings.cdp_connect_timeout_ms,
                slow_mo=settings.slow_mo_ms,
            )
            contexts = browser.contexts
            if not contexts:
                raise RuntimeError('CDP已连接，但未获取到默认BrowserContext')
            context = contexts[0]
            browser_cdp = browser.new_browser_cdp_session()
            runtime = BrowserRuntime(
                playwright=playwright,
                browser=browser,
                context=context,
                browser_cdp=browser_cdp,
                lock=threading.RLock(),
            )
            self._browser_runtime = runtime
            self._log_cdp_diagnostics(runtime)
            logger.info('浏览器运行时挂接成功, debugPort=%s, pageCount=%s', settings.debug_port, len(context.pages))
            return runtime
        except Exception as exc:
            if browser_cdp is not None:
                self._quietly_detach_cdp(browser_cdp)
            if browser is not None:
                self._quietly_close_browser(browser)
            if playwright is not None:
                self._quietly_stop_playwright(playwright)
            raise RuntimeError(f'挂接浏览器运行时失败: {exc.__class__.__name__}: {exc}') from exc

    def _is_browser_runtime_alive(self, runtime: BrowserRuntime) -> bool:
        try:
            if not is_port_open('127.0.0.1', settings.debug_port):
                return False
            if not runtime.browser.is_connected():
                return False
            _ = runtime.context.pages
            runtime.browser_cdp.send('Browser.getVersion')
            return True
        except Exception as exc:
            logger.warning('检测到浏览器运行时已失效，准备重建, msg=%s', exc)
            return False

    def _shutdown_browser_runtime(self) -> None:
        runtime = self._browser_runtime
        self._browser_runtime = None
        if runtime is None:
            return
        self._quietly_detach_cdp(runtime.browser_cdp)
        self._quietly_close_browser(runtime.browser)
        self._quietly_stop_playwright(runtime.playwright)

    def _get_valid_window_runtime(self, db: Session, window_id: str) -> tuple[WindowRuntime, AdBrowserWindow]:
        db_window = self._select_window_by_window_id(db, window_id)
        if db_window is None:
            raise ValueError(f'windowId不存在: {window_id}')
        if db_window.status != '1':
            raise ValueError(f'windowId已失效: {window_id}')
        if self._browser_runtime is None or not self._is_browser_runtime_alive(self._browser_runtime):
            raise RuntimeError(f'windowId有效，但浏览器运行时未挂接，请先调用重开接口恢复: {window_id}')
        runtime = self._window_runtime_map.get(window_id)
        if runtime is None:
            raise RuntimeError(f'windowId有效，但窗口运行时未恢复，请先调用重开接口恢复: {window_id}')
        return runtime, db_window

    # ----------------------------- page/window operations -----------------------------
    def _create_cdp_http_page_record(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        url: str,
        status: str,
        sort_no: int,
    ) -> AdBrowserPage:
        safe_url = url or 'about:blank'
        target_payload = self._open_url_by_cdp_http(safe_url)
        page_title = str(target_payload.get('title') or '')
        page_url = str(target_payload.get('url') or safe_url)
        return self._create_page_record(
            db=db,
            window_row_id=db_window.id,
            title=page_title,
            url=page_url,
            status=status,
            sort_no=sort_no,
        )

    def _resolve_cdp_http_page_row(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        page_id: str | None,
        url_contains: str | None,
    ) -> AdBrowserPage:
        page_rows = self._select_valid_page_rows(db, db_window.id)
        if page_id:
            page_db_id = self._parse_page_id(page_id)
            for row in page_rows:
                if row.id == page_db_id:
                    return row
            raise ValueError(f'pageId不存在或已失效: {page_id}')
        if url_contains:
            for row in reversed(page_rows):
                if url_contains in (row.url or ''):
                    return row
        active_row = next((row for row in page_rows if row.status == '1'), None)
        if active_row is not None:
            return active_row
        if page_rows:
            return page_rows[-1]
        return self._create_page_record(
            db=db,
            window_row_id=db_window.id,
            title='',
            url=settings.start_url or 'about:blank',
            status='1',
            sort_no=1,
        )

    def _create_new_browser_window_page(self, browser_runtime: BrowserRuntime, url: str) -> Page:
        safe_url = url or 'about:blank'

        if self._is_native_open_page_mode():
            logger.info('使用原生Chrome命令行方式创建新窗口, url=%s', safe_url)
            return self._do_create_new_browser_window_page(browser_runtime, safe_url)

        try:
            return self._do_cdp_create_new_browser_window_page(browser_runtime, safe_url)
        except Exception as exc:
            if not self._should_rebuild_browser_runtime(exc):
                raise
            logger.warning('CDP创建窗口时检测到运行时已关闭，准备重建后重试, msg=%s', exc)
            fresh_runtime, _ = self._rebuild_browser_runtime()
            return self._do_create_new_browser_window_page(fresh_runtime, safe_url)

    def _do_create_new_browser_window_page(self, browser_runtime: BrowserRuntime, url: str) -> Page:
        with browser_runtime.lock:
            before_page_ids = {id(page) for page in self._get_alive_pages(browser_runtime.context.pages)}
            browser_process = self._launch_browser_new_window_process(url)
            logger.info('requested native Chrome new window, pid=%s, url=%s', browser_process.pid, url)
            page = self._wait_for_new_page(browser_runtime.context, before_page_ids, url)
            self._wait_for_domcontentloaded_quietly(page, settings.start_timeout_ms)
            return page

    def _do_cdp_create_new_browser_window_page(self, browser_runtime: BrowserRuntime, url: str) -> Page:
        with browser_runtime.lock:
            before_page_ids = {id(page) for page in self._get_alive_pages(browser_runtime.context.pages)}
            safe_url = url or 'about:blank'
            try:
                result = browser_runtime.browser_cdp.send(
                    "Target.createTarget",
                    {"url": safe_url, "newWindow": True},
                )
                target_id = result.get("targetId", "")
                logger.info("CDP创建新浏览器窗口成功, targetId=%s, url=%s", target_id, safe_url)
            except Exception as exc:
                logger.warning("CDP创建新窗口失败，回退到子进程方式, msg=%s", exc)
                return self._do_create_new_browser_window_page(browser_runtime, safe_url)
            page = self._wait_for_new_page(browser_runtime.context, before_page_ids, safe_url)
            self._wait_for_domcontentloaded_quietly(page, settings.start_timeout_ms)
            return page

    def _should_rebuild_browser_runtime(self, exc: Exception) -> bool:
        if isinstance(exc, (BrokenPipeError, ConnectionError, ConnectionResetError, OSError)):
            return True
        if isinstance(exc, Error):
            message = str(exc).lower()
            return 'has been closed' in message or 'target closed' in message or 'browser has been closed' in message
        return False

    def _acquire_window_root_page(self, browser_runtime: BrowserRuntime, launched_now: bool, url: str) -> Page:
        safe_url = url or 'about:blank'
        if not launched_now:
            return self._create_new_browser_window_page(browser_runtime, safe_url)

        with browser_runtime.lock:
            tracked_page_ids = self._all_tracked_page_object_ids()
            existing_pages = [
                page
                for page in self._get_alive_pages(browser_runtime.context.pages)
                if id(page) not in tracked_page_ids
            ]
            if existing_pages:
                page = self._pick_new_window_page(existing_pages, safe_url)
                current_url = self._safe_url(page)
                if safe_url and safe_url != 'about:blank' and current_url != safe_url:
                    try:
                        page.goto(safe_url, wait_until='domcontentloaded', timeout=settings.start_timeout_ms)
                    except Exception:
                        self._wait_for_domcontentloaded_quietly(page, settings.start_timeout_ms)
                else:
                    self._wait_for_domcontentloaded_quietly(page, settings.start_timeout_ms)
                return page

        return self._create_new_browser_window_page(browser_runtime, safe_url)

    def _create_managed_page_in_window(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        url: str,
        active: bool,
    ) -> tuple[AdBrowserPage, Page]:
        opener_row, opener_page = self._resolve_anchor_page_for_window(db, db_window, window_runtime)
        page = self._open_child_page(opener_page, url)
        next_sort_no = self._next_sort_no(db, db_window.id)
        page_row = self._create_page_record(
            db=db,
            window_row_id=db_window.id,
            title=self._safe_title(page),
            url=self._safe_url(page),
            status='1' if active else '0',
            sort_no=next_sort_no,
        )
        window_runtime.page_map[page_row.id] = page
        if active:
            self._set_active_page(db, db_window, window_runtime, page_row.id)
        else:
            try:
                opener_page.bring_to_front()
            except Exception:
                pass
            self._update_window_last_page_info(db, db_window, self._safe_title(opener_page), self._safe_url(opener_page))
        return page_row, page

    def _open_pages_batch_in_window(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        root_page: Page,
        items: list[BatchOpenPageItem],
        start_sort_no: int,
    ) -> list[AdBrowserPage]:
        rows: list[AdBrowserPage] = []
        sort_no = start_sort_no
        opener = root_page
        for item in items:
            page = self._open_child_page(opener, item.url)
            row = self._create_page_record(
                db=db,
                window_row_id=db_window.id,
                title=self._safe_title(page),
                url=self._safe_url(page),
                status='1' if item.active else '0',
                sort_no=sort_no,
            )
            window_runtime.page_map[row.id] = page
            rows.append(row)
            sort_no += 1
            if item.active:
                try:
                    page.bring_to_front()
                except Exception:
                    pass
                opener = page
            else:
                try:
                    opener.bring_to_front()
                except Exception:
                    pass
        return rows

    def _open_child_page(self, opener_page: Page, url: str) -> Page:
        browser_runtime = self._browser_runtime
        if browser_runtime is None:
            raise RuntimeError('浏览器运行时未挂接')

        safe_url = url or 'about:blank'

        if self._is_native_open_page_mode():
            logger.info('使用原生Chrome命令行方式打开子页面, url=%s', safe_url)
            return self._create_new_browser_window_page(browser_runtime, safe_url)

        with browser_runtime.lock:
            with opener_page.expect_popup(timeout=max(settings.start_timeout_ms, 10_000)) as popup_info:
                opener_page.evaluate('(targetUrl) => window.open(targetUrl, "_blank")', safe_url)
            page = popup_info.value

        self._wait_for_domcontentloaded_quietly(page, settings.start_timeout_ms)
        return page

    def _wait_for_new_page(self, context: BrowserContext, before_page_ids: set[int], expected_url: str | None = None) -> Page:
        deadline = time.time() + max(settings.start_timeout_ms, 10_000) / 1000
        fallback_page: Page | None = None
        seen_urls: list[str] = []
        while time.time() < deadline:
            pages = self._get_alive_pages(context.pages)
            for page in reversed(pages):
                if id(page) not in before_page_ids:
                    current_url = self._safe_url(page)
                    if current_url not in seen_urls:
                        seen_urls.append(current_url)
                    if self._is_expected_new_page(current_url, expected_url):
                        return page
                    if fallback_page is None and not self._is_auxiliary_chrome_page(current_url):
                        fallback_page = page
            time.sleep(0.2)
        if fallback_page is not None:
            logger.warning(
                'new page URL did not match before timeout, using captured page, expectedUrl=%s, seenUrls=%s',
                expected_url,
                seen_urls,
            )
            return fallback_page
        raise RuntimeError(f'wait for native Chrome window page timeout: expectedUrl={expected_url}, seenUrls={seen_urls}')

    def _pick_new_window_page(self, pages: list[Page], expected_url: str | None) -> Page:
        fallback_page: Page | None = None
        for page in reversed(pages):
            current_url = self._safe_url(page)
            if self._is_expected_new_page(current_url, expected_url):
                return page
            if fallback_page is None and not self._is_auxiliary_chrome_page(current_url):
                fallback_page = page
        return fallback_page or pages[-1]

    def _resolve_anchor_page_for_window(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
    ) -> tuple[AdBrowserPage, Page]:
        active_row = self._select_active_page_row(db, db_window.id)
        if active_row is not None and active_row.id in window_runtime.page_map:
            return active_row, window_runtime.page_map[active_row.id]
        valid_rows = self._select_valid_page_rows(db, db_window.id)
        for row in reversed(valid_rows):
            page = window_runtime.page_map.get(row.id)
            if page is not None and not page.is_closed():
                return row, page
        raise RuntimeError(f'windowId下没有可用锚点页面: {db_window.window_id}')

    def _resolve_managed_page(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page_id: str | None,
        url_contains: str | None,
    ) -> tuple[AdBrowserPage, Page]:
        valid_rows = self._select_valid_page_rows(db, db_window.id)
        if not valid_rows:
            raise RuntimeError('当前窗口下没有页面可操作')

        target_row: AdBrowserPage | None = None
        if page_id:
            page_db_id = self._parse_page_id(page_id)
            target_row = next((row for row in valid_rows if row.id == page_db_id), None)
            if target_row is None:
                raise ValueError(f'pageId不存在: {page_id}')
        elif url_contains:
            for row in reversed(valid_rows):
                if url_contains in (row.url or ''):
                    target_row = row
                    break
            if target_row is None:
                raise ValueError(f'未找到url包含指定关键字的页面: {url_contains}')
        else:
            target_row = next((row for row in valid_rows if row.status == '1'), valid_rows[-1])

        page = window_runtime.page_map.get(target_row.id)
        if page is None or page.is_closed():
            raise RuntimeError(f'pageId存在，但运行时页面已丢失，请调用重开接口恢复: {self._page_id_by_db_id(target_row.id)}')
        return target_row, page

    def _resolve_takeover_page(self, window_runtime: WindowRuntime, url_contains: Optional[str]) -> Page:
        browser_runtime = self._browser_runtime
        if browser_runtime is None:
            raise RuntimeError('浏览器运行时未挂接')
        tracked_page_ids = self._all_tracked_page_object_ids()
        deadline = time.time() + max(getattr(settings, 'takeover_stabilize_wait_ms', 1500), 1200) / 1000
        last_candidate: Optional[Page] = None

        while time.time() < deadline:
            alive_pages = self._get_alive_pages(browser_runtime.context.pages)
            candidate_pool = [page for page in alive_pages if id(page) not in tracked_page_ids]
            if not candidate_pool:
                candidate_pool = alive_pages
            if not candidate_pool:
                raise RuntimeError('当前浏览器下没有页面可接管')

            candidate = self._pick_target_page(candidate_pool, url_contains)
            last_candidate = candidate
            self._wait_for_domcontentloaded_quietly(candidate, getattr(settings, 'takeover_each_wait_ms', 800))
            current_url = self._safe_url(candidate)
            if self._is_page_ready(candidate, current_url, url_contains, len(candidate_pool)):
                return candidate
            time.sleep(getattr(settings, 'takeover_retry_interval_ms', 150) / 1000)

        if last_candidate is None:
            raise RuntimeError('当前浏览器下没有页面可接管')
        self._wait_for_domcontentloaded_quietly(last_candidate, getattr(settings, 'takeover_fallback_wait_ms', 300))
        return last_candidate

    def _find_page_row_by_object(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page: Page,
    ) -> AdBrowserPage | None:
        for page_db_id, runtime_page in window_runtime.page_map.items():
            if runtime_page is page:
                return db.query(AdBrowserPage).filter(AdBrowserPage.id == page_db_id).one_or_none()
        return None

    def _adopt_untracked_page(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page: Page,
    ) -> AdBrowserPage:
        row = self._create_page_record(
            db=db,
            window_row_id=db_window.id,
            title=self._safe_title(page),
            url=self._safe_url(page),
            status='0',
            sort_no=self._next_sort_no(db, db_window.id),
        )
        window_runtime.page_map[row.id] = page
        return row

    def _set_active_page(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        active_page_db_id: int | None,
    ) -> None:
        page_rows = self._select_valid_page_rows(db, db_window.id)
        active_row: AdBrowserPage | None = None
        for row in page_rows:
            row.status = '1' if active_page_db_id is not None and row.id == active_page_db_id else '0'
            if row.status == '1':
                active_row = row
        db.commit()
        window_runtime.active_page_db_id = active_page_db_id
        if active_row is not None:
            active_page = window_runtime.page_map.get(active_row.id)
            if active_page is not None:
                try:
                    active_page.bring_to_front()
                except Exception:
                    pass
            self._update_window_last_page_info(db, db_window, active_row.title, active_row.url)
        else:
            self._update_window_last_page_info(db, db_window, None, None)

    def _sync_active_status_from_runtime(self, db: Session, db_window: AdBrowserWindow, window_runtime: WindowRuntime) -> None:
        valid_rows = self._select_valid_page_rows(db, db_window.id)
        if not valid_rows:
            window_runtime.active_page_db_id = None
            self._update_window_last_page_info(db, db_window, None, None)
            return
        active_row = None
        if window_runtime.active_page_db_id is not None:
            active_row = next((row for row in valid_rows if row.id == window_runtime.active_page_db_id), None)
        if active_row is None:
            active_row = next((row for row in valid_rows if row.status == '1'), valid_rows[-1])
        self._set_active_page(db, db_window, window_runtime, active_row.id)

    def _sync_window_snapshots(self, db: Session, db_window: AdBrowserWindow, window_runtime: WindowRuntime) -> None:
        valid_rows = self._select_valid_page_rows(db, db_window.id)
        for row in valid_rows:
            page = window_runtime.page_map.get(row.id)
            if page is None or page.is_closed():
                continue
            self._sync_page_snapshot(db, row, page, auto_commit=False)
        db.commit()
        active_row = next((row for row in valid_rows if row.status == '1'), None)
        self._update_window_last_page_info(db, db_window, active_row.title if active_row else None, active_row.url if active_row else None)

    def _sync_page_snapshot(self, db: Session, page_row: AdBrowserPage, page: Page, auto_commit: bool = True) -> None:
        page_row.title = self._safe_title(page)[:255] if self._safe_title(page) else None
        url = self._safe_url(page)
        page_row.url = url[:1000] if url else None
        if auto_commit:
            db.commit()

    def _invalidate_page_local(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page_db_id: int,
        close_page: bool,
    ) -> None:
        page_row = db.query(AdBrowserPage).filter(AdBrowserPage.id == page_db_id).one_or_none()
        if page_row is None or page_row.status == '2':
            return
        runtime_page = window_runtime.page_map.pop(page_db_id, None)
        if close_page and runtime_page is not None:
            try:
                runtime_page.close()
            except Exception:
                pass
        page_row.status = '2'
        page_row.invalid_time = datetime.now()
        db.commit()
        if window_runtime.active_page_db_id == page_db_id:
            window_runtime.active_page_db_id = None

    def _invalidate_window_local(self, db: Session, window_id: str, close_pages: bool) -> bool:
        db_window = self._select_window_by_window_id(db, window_id)
        if db_window is None:
            raise ValueError(f'windowId不存在: {window_id}')

        runtime = self._window_runtime_map.pop(window_id, None)
        closed = False
        if runtime is not None:
            with runtime.lock:
                for page in list(runtime.page_map.values()):
                    if not close_pages:
                        continue
                    try:
                        page.close()
                        closed = True
                    except Exception:
                        pass
                runtime.page_map.clear()

        page_rows = (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == db_window.id, AdBrowserPage.status.in_(['0', '1']))
            .all()
        )
        now = datetime.now()
        for page_row in page_rows:
            page_row.status = '2'
            page_row.invalid_time = now
        db_window.status = '0'
        db_window.invalid_time = now
        db_window.last_page_title = None
        db_window.last_page_url = None
        db.commit()

        if self._browser_runtime is not None and not self._window_runtime_map:
            self._shutdown_browser_runtime()
            closed = True
        return closed

    # ----------------------------- db helpers -----------------------------
    def _select_window_by_window_id(self, db: Session, window_id: str) -> Optional[AdBrowserWindow]:
        return db.query(AdBrowserWindow).filter(AdBrowserWindow.window_id == window_id).one_or_none()

    def _select_valid_page_rows(self, db: Session, window_row_id: int) -> list[AdBrowserPage]:
        return (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status.in_(['0', '1']))
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .all()
        )

    def _select_valid_page_config_rows(self, db: Session, config_code: str) -> list[AdBrowserPageConfig]:
        return (
            db.query(AdBrowserPageConfig)
            .filter(
                AdBrowserPageConfig.config_code == config_code,
                AdBrowserPageConfig.status == '1',
                AdBrowserPageConfig.url != '',
            )
            .order_by(AdBrowserPageConfig.sort_no.asc(), AdBrowserPageConfig.id.asc())
            .all()
        )

    def _select_active_page_row(self, db: Session, window_row_id: int) -> Optional[AdBrowserPage]:
        return (
            db.query(AdBrowserPage)
            .filter(AdBrowserPage.window_id == window_row_id, AdBrowserPage.status == '1')
            .order_by(AdBrowserPage.sort_no.asc(), AdBrowserPage.id.asc())
            .one_or_none()
        )

    def _create_page_record(
        self,
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

    def _next_sort_no(self, db: Session, window_row_id: int) -> int:
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

    def _invalidate_window_rows(self, db: Session, window_row_id: int) -> None:
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

    def _update_window_last_page_info(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        title: str | None,
        url: str | None,
    ) -> None:
        db_window.last_page_title = title[:255] if title else None
        db_window.last_page_url = url[:500] if url else None
        db.commit()

    # ----------------------------- misc helpers -----------------------------
    def _page_id_by_db_id(self, page_db_id: int) -> str:
        return f'page-{page_db_id}'

    def _parse_page_id(self, page_id: str) -> int:
        lower = page_id.strip().lower()
        if not lower.startswith('page-'):
            raise ValueError(f'pageId格式不正确: {page_id}，示例: page-123')
        suffix = lower.split('-', 1)[1]
        if not suffix.isdigit():
            raise ValueError(f'pageId格式不正确: {page_id}，示例: page-123')
        return int(suffix)

    def _build_page_info_response(
        self,
        db: Session,
        db_window: AdBrowserWindow,
        window_runtime: WindowRuntime,
        page_row: AdBrowserPage,
    ) -> PageInfoResponse:
        valid_rows = self._select_valid_page_rows(db, db_window.id)
        page_index = next(index for index, row in enumerate(valid_rows, start=1) if row.id == page_row.id)
        return PageInfoResponse(
            windowId=db_window.window_id,
            sessionId=db_window.window_id,
            pageId=self._page_id_by_db_id(page_row.id),
            pageIndex=page_index,
            title=page_row.title or '',
            url=page_row.url or '',
            status=page_row.status,
        )

    def _all_tracked_page_object_ids(self) -> set[int]:
        tracked: set[int] = set()
        for runtime in self._window_runtime_map.values():
            tracked.update(id(page) for page in runtime.page_map.values())
        return tracked

    def _get_alive_pages(self, pages: list[Page]) -> list[Page]:
        result: list[Page] = []
        for page in pages:
            try:
                if not page.is_closed():
                    result.append(page)
            except Exception:
                continue
        return result

    def _pick_target_page(self, pages: list[Page], url_contains: Optional[str]) -> Page:
        if url_contains:
            for page in reversed(pages):
                url = self._safe_url(page)
                if url_contains in url and not self._is_blank_like_url(url):
                    return page
            for page in reversed(pages):
                url = self._safe_url(page)
                if url_contains in url:
                    return page

        for page in reversed(pages):
            url = self._safe_url(page)
            if not self._is_blank_like_url(url):
                return page
        return pages[-1]

    def _wait_for_domcontentloaded_quietly(self, page: Page, timeout_ms: int) -> None:
        try:
            page.wait_for_load_state('domcontentloaded', timeout=timeout_ms)
        except Exception:
            pass

    def _is_page_ready(self, page: Page, current_url: str, url_contains: Optional[str], total_pages: int) -> bool:
        if url_contains:
            return url_contains in current_url
        if total_pages > 1 and self._is_blank_like_url(current_url):
            return False
        return bool(current_url)

    def _is_blank_like_url(self, url: str) -> bool:
        if not url:
            return True
        lower_url = url.lower()
        return (
            lower_url == 'about:blank'
            or lower_url.startswith('chrome://newtab')
            or lower_url.startswith('chrome://newtab-footer')
            or lower_url.startswith('chrome://new-tab-page')
            or lower_url.startswith('edge://newtab')
            or lower_url.startswith('data:,')
        )

    def _is_expected_new_page(self, current_url: str, expected_url: str | None) -> bool:
        if expected_url is None:
            return True
        if current_url == expected_url:
            return True
        if expected_url == 'about:blank':
            return self._is_blank_like_url(current_url) and not self._is_auxiliary_chrome_page(current_url)
        return not self._is_blank_like_url(current_url)

    def _is_auxiliary_chrome_page(self, url: str) -> bool:
        lower_url = (url or '').lower()
        return lower_url.startswith('chrome://newtab-footer')

    def _safe_url(self, page: Page) -> str:
        try:
            return page.url or ''
        except Error:
            return ''

    def _safe_title(self, page: Page) -> str:
        try:
            return page.title() or ''
        except Error:
            return ''

    def _build_cdp_url(self) -> str:
        return f'http://127.0.0.1:{settings.debug_port}'

    def _is_native_open_page_mode(self) -> bool:
        return (settings.open_page_mode or '').strip().lower() == 'native'

    def _is_cdp_http_open_page_mode(self) -> bool:
        return (settings.open_page_mode or '').strip().lower() in {'cdp_http', 'cdp-http', 'cdphttp', 'http'}

    def _open_url_by_cdp_http(self, url: str) -> dict:
        safe_url = url or 'about:blank'
        encoded_url = quote(safe_url, safe='')
        endpoint = f'{self._build_cdp_url()}/json/new?{encoded_url}'
        timeout = max(settings.cdp_http_open_timeout_ms / 1000, 1)
        try:
            payload = put_json(endpoint, timeout=timeout)
        except Exception as exc:
            logger.warning('CDP HTTP PUT /json/new 失败，尝试 GET 回退, url=%s, msg=%s', safe_url, exc)
            payload = get_json(endpoint, timeout=timeout)
        if not isinstance(payload, dict):
            raise RuntimeError(f'CDP HTTP打开页面返回值异常: type={type(payload).__name__}, payload={payload}')
        logger.info(
            'CDP HTTP打开页面请求成功, targetId=%s, url=%s',
            payload.get('id') or payload.get('targetId'),
            payload.get('url') or safe_url,
        )
        return payload

    def _create_selenium_driver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
        except ImportError as exc:
            raise RuntimeError('缺少 selenium 依赖，请先执行: uv add selenium') from exc

        options = Options()
        options.debugger_address = f'127.0.0.1:{settings.debug_port}'
        if settings.browser_executable_path:
            options.binary_location = settings.browser_executable_path

        chromedriver_path = (settings.selenium_chromedriver_path or '').strip()
        if chromedriver_path:
            service = Service(chromedriver_path)
            return webdriver.Chrome(service=service, options=options)
        return webdriver.Chrome(options=options)

    def _open_config_pages_by_selenium_once(
        self,
        db: Session,
        config_code: str,
        new_window: bool | None,
        ensure_browser: bool,
    ) -> BatchOpenPagesResponse:
        safe_config_code = (config_code or '').strip()
        if not safe_config_code:
            raise ValueError('configCode cannot be empty')

        self._ensure_profile_dir()
        self._ensure_browser_executable_path()
        config_rows = self._select_valid_page_config_rows(db, safe_config_code)
        if not config_rows:
            raise ValueError(f'no valid page config found: configCode={safe_config_code}')

        window_id = uuid.uuid4().hex
        db_window = AdBrowserWindow(window_id=window_id, status='1')
        db.add(db_window)
        db.commit()

        browser_started_now = False
        driver = None
        opened_rows: list[AdBrowserPage] = []
        use_new_window = settings.selenium_browser_new_window if new_window is None else bool(new_window)
        try:
            if not is_port_open('127.0.0.1', settings.debug_port):
                if not ensure_browser:
                    raise RuntimeError(f'Chrome调试端口未启动: 127.0.0.1:{settings.debug_port}')
                browser_process = self._launch_browser_pure_process('', False)
                browser_started_now = True
                self._wait_for_cdp_ready(browser_process)

            driver = self._create_selenium_driver()
            page_load_timeout = max(settings.selenium_page_load_timeout_ms / 1000, 1)
            try:
                driver.set_page_load_timeout(page_load_timeout)
            except Exception as exc:
                logger.warning('Selenium设置页面加载超时失败，继续执行, msg=%s', exc)

            sort_no = 1
            for index, config_row in enumerate(config_rows):
                safe_url = config_row.url or 'about:blank'
                active = index == len(config_rows) - 1
                if use_new_window or index > 0:
                    try:
                        driver.switch_to.new_window('window')
                    except Exception as exc:
                        logger.warning('Selenium新建窗口失败，继续尝试在当前窗口打开, url=%s, msg=%s', safe_url, exc)

                try:
                    driver.execute_script('window.location.href = arguments[0];', safe_url)
                except Exception as exc:
                    logger.warning('Selenium execute_script跳转失败，尝试 driver.get, url=%s, msg=%s', safe_url, exc)
                    try:
                        driver.get(safe_url)
                    except Exception as get_exc:
                        logger.warning('Selenium driver.get未正常完成，浏览器可能已开始加载，继续记录, url=%s, msg=%s', safe_url, get_exc)

                time.sleep(0.2)
                page_title = ''
                page_url = safe_url
                if settings.selenium_read_page_info:
                    try:
                        page_url = driver.current_url or safe_url
                    except Exception:
                        page_url = safe_url
                    try:
                        page_title = driver.title or ''
                    except Exception:
                        page_title = ''

                row = self._create_page_record(
                    db=db,
                    window_row_id=db_window.id,
                    title=page_title,
                    url=page_url,
                    status='1' if active else '0',
                    sort_no=sort_no,
                )
                opened_rows.append(row)
                sort_no += 1

            if opened_rows:
                self._update_window_last_page_info(db, db_window, opened_rows[-1].title, opened_rows[-1].url)

            logger.info(
                'Selenium短接管打开配置页完成, windowId=%s, configCode=%s, opened=%s, browserStartedNow=%s, driverWillDetach=True',
                window_id,
                safe_config_code,
                len(opened_rows),
                browser_started_now,
            )
            return BatchOpenPagesResponse(
                windowId=window_id,
                sessionId=window_id,
                configCode=safe_config_code,
                total=len(opened_rows),
                openedPages=[
                    self._build_page_info_response(db, db_window, WindowRuntime(active_page_db_id=opened_rows[-1].id if opened_rows else None), row)
                    for row in opened_rows
                ],
            )
        except Exception as exc:
            logger.exception('Selenium短接管打开配置页失败, windowId=%s, configCode=%s, msg=%s', window_id, safe_config_code, exc)
            self._invalidate_window_rows(db, db_window.id)
            raise
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception as exc:
                    logger.warning('Selenium短接管 driver.quit 失败，继续返回, msg=%s', exc)

    def _open_config_pages_by_playwright_once(
        self,
        db: Session,
        config_code: str,
        new_window: bool | None,
        ensure_browser: bool,
    ) -> BatchOpenPagesResponse:
        safe_config_code = (config_code or '').strip()
        if not safe_config_code:
            raise ValueError('configCode cannot be empty')

        self._ensure_profile_dir()
        self._ensure_browser_executable_path()
        config_rows = self._select_valid_page_config_rows(db, safe_config_code)
        if not config_rows:
            raise ValueError(f'no valid page config found: configCode={safe_config_code}')

        window_id = uuid.uuid4().hex
        db_window = AdBrowserWindow(window_id=window_id, status='1')
        db.add(db_window)
        db.commit()

        opened_rows: list[AdBrowserPage] = []
        browser_started_now = False
        use_new_window = settings.playwright_once_new_window if new_window is None else bool(new_window)
        playwright: Playwright | None = None
        browser: Browser | None = None
        try:
            if not is_port_open('127.0.0.1', settings.debug_port):
                if not ensure_browser:
                    raise RuntimeError(f'Chrome调试端口未启动: 127.0.0.1:{settings.debug_port}')
                browser_process = self._launch_browser_pure_process('', False)
                browser_started_now = True
                self._wait_for_cdp_ready(browser_process)

            ensure_windows_proactor_event_loop_policy()
            self._log_event_loop_policy('before_playwright_once_attach')
            playwright = sync_playwright().start()
            browser = playwright.chromium.connect_over_cdp(
                self._build_cdp_url(),
                timeout=settings.playwright_once_connect_timeout_ms,
                slow_mo=0,
            )
            context = browser.contexts[0] if browser.contexts else browser.new_context()

            sort_no = 1
            reusable_page: Page | None = None
            if not use_new_window:
                alive_pages = self._get_alive_pages(context.pages)
                reusable_page = alive_pages[-1] if alive_pages else None

            for index, config_row in enumerate(config_rows):
                safe_url = config_row.url or 'about:blank'
                active = index == len(config_rows) - 1
                page: Page | None = None
                if use_new_window or reusable_page is None or index > 0:
                    try:
                        page = context.new_page()
                    except Exception as exc:
                        logger.warning('Playwright短接管 new_page 失败，尝试复用现有页面, url=%s, msg=%s', safe_url, exc)
                        alive_pages = self._get_alive_pages(context.pages)
                        page = alive_pages[-1] if alive_pages else None
                else:
                    page = reusable_page

                if page is None:
                    raise RuntimeError('Playwright短接管未找到可用页面')

                try:
                    page.evaluate('(targetUrl) => { window.location.href = targetUrl; return true; }', safe_url)
                except Exception as exc:
                    logger.warning('Playwright短接管 evaluate跳转失败，尝试 goto(commit), url=%s, msg=%s', safe_url, exc)
                    try:
                        page.goto(
                            safe_url,
                            wait_until='commit',
                            timeout=settings.playwright_once_navigation_timeout_ms,
                        )
                    except Exception as goto_exc:
                        logger.warning('Playwright短接管 goto 未正常完成，浏览器可能已开始加载，继续记录, url=%s, msg=%s', safe_url, goto_exc)

                time.sleep(0.2)
                page_title = ''
                page_url = safe_url
                if settings.playwright_once_read_page_info:
                    page_title = self._safe_title(page)
                    page_url = self._safe_url(page) or safe_url

                row = self._create_page_record(
                    db=db,
                    window_row_id=db_window.id,
                    title=page_title,
                    url=page_url,
                    status='1' if active else '0',
                    sort_no=sort_no,
                )
                opened_rows.append(row)
                sort_no += 1

            if opened_rows:
                self._update_window_last_page_info(db, db_window, opened_rows[-1].title, opened_rows[-1].url)

            logger.info(
                'Playwright短接管打开配置页完成, windowId=%s, configCode=%s, opened=%s, browserStartedNow=%s, willDetach=True',
                window_id,
                safe_config_code,
                len(opened_rows),
                browser_started_now,
            )
            active_id = opened_rows[-1].id if opened_rows else None
            response_runtime = WindowRuntime(active_page_db_id=active_id, root_page_db_id=opened_rows[0].id if opened_rows else None)
            return BatchOpenPagesResponse(
                windowId=window_id,
                sessionId=window_id,
                configCode=safe_config_code,
                total=len(opened_rows),
                openedPages=[
                    self._build_page_info_response(db, db_window, response_runtime, row)
                    for row in opened_rows
                ],
            )
        except Exception as exc:
            logger.exception('Playwright短接管打开配置页失败, windowId=%s, configCode=%s, msg=%s', window_id, safe_config_code, exc)
            self._invalidate_window_rows(db, db_window.id)
            raise
        finally:
            # 不调用 browser.close()，避免把用户正在使用的 Chrome 关掉；只停止本次 Playwright 驱动连接。
            if playwright is not None:
                try:
                    playwright.stop()
                except Exception as exc:
                    logger.warning('Playwright短接管 stop 失败，继续返回, msg=%s', exc)

    def _ensure_profile_dir(self) -> None:
        os.makedirs(settings.profile_dir, exist_ok=True)

    def _ensure_browser_executable_path(self) -> None:
        if not os.path.isfile(settings.browser_executable_path):
            raise FileNotFoundError(f'浏览器可执行文件不存在: {settings.browser_executable_path}')

    def _launch_browser_process(self) -> subprocess.Popen:
        start_url = settings.start_url or 'about:blank'
        command = self._build_browser_process_command(start_url)
        logger.info(
            'starting Chrome process, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_process(command)

    def _launch_browser_new_window_process(self, url: str) -> subprocess.Popen:
        command = self._build_browser_process_command(url or 'about:blank')
        logger.info(
            'starting native Chrome new window, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_process(command)

    def _launch_browser_pure_process(self, url: str, new_window: bool) -> subprocess.Popen:
        command = self._build_browser_pure_command(url, new_window)
        logger.info(
            'starting Chrome process by pure mode, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_pure_process(command)

    def _build_browser_pure_command(self, url: str, new_window: bool) -> list[str]:
        command = [
            settings.browser_executable_path,
            f'--remote-debugging-port={settings.debug_port}',
            f'--user-data-dir={settings.profile_dir}',
        ]
        if new_window:
            command.append('--new-window')
        safe_url = (url or '').strip()
        if safe_url:
            command.append(safe_url)
        return command

    def _build_browser_process_command(self, url: str) -> list[str]:
        command = [
            settings.browser_executable_path,
            f'--remote-debugging-port={settings.debug_port}',
            f'--user-data-dir={settings.profile_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--new-window',
        ]
        if settings.headless:
            command.append('--headless=new')
        if url:
            command.append(url)
        return command

    def _popen_browser_pure_process(self, command: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )

    def _popen_browser_process(self, command: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )

    def _wait_for_cdp_ready(self, browser_process: subprocess.Popen) -> None:
        deadline = time.time() + settings.cdp_ready_max_wait_ms / 1000
        version_url = f'http://127.0.0.1:{settings.debug_port}/json/version'
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            return_code = browser_process.poll()
            if return_code is not None:
                stderr_text = ''
                stdout_text = ''
                try:
                    if browser_process.stderr is not None:
                        stderr_text = browser_process.stderr.read()
                except Exception:
                    pass
                try:
                    if browser_process.stdout is not None:
                        stdout_text = browser_process.stdout.read()
                except Exception:
                    pass
                raise RuntimeError(
                    '浏览器进程已提前退出, '
                    f'returnCode={return_code}, stderr={stderr_text.strip() or "<empty>"}, stdout={stdout_text.strip() or "<empty>"}'
                )
            try:
                if is_port_open('127.0.0.1', settings.debug_port):
                    payload = get_json(version_url, timeout=2)
                    websocket_url = payload.get('webSocketDebuggerUrl')
                    logger.info('CDP探测成功, versionUrl=%s, websocket=%s', version_url, websocket_url)
                    if websocket_url:
                        return
            except Exception as exc:
                last_error = exc
            time.sleep(settings.cdp_ready_retry_interval_ms / 1000)
        raise RuntimeError(f'等待CDP就绪超时: {last_error}')

    def _log_cdp_diagnostics(self, runtime: BrowserRuntime) -> None:
        try:
            version = runtime.browser_cdp.send('Browser.getVersion')
            logger.info(
                'Chrome diagnostics, product=%s, userAgent=%s, profileDir=%s, debugPort=%s, pageCount=%s',
                version.get('product'),
                version.get('userAgent'),
                settings.profile_dir,
                settings.debug_port,
                len(runtime.context.pages),
            )
        except Exception as exc:
            logger.warning('Chrome version diagnostics failed, msg=%s', exc)

        try:
            targets = get_json(f'http://127.0.0.1:{settings.debug_port}/json/list', timeout=2)
            if not isinstance(targets, list):
                logger.warning('CDP target diagnostics returned non-list payload, type=%s', type(targets).__name__)
                return

            extension_pages = [
                target
                for target in targets
                if str(target.get('url', '')).startswith('chrome-extension://')
                and target.get('type') == 'page'
            ]
            extension_workers = [
                target
                for target in targets
                if str(target.get('url', '')).startswith('chrome-extension://')
                and target.get('type') in {'service_worker', 'background_page'}
            ]
            logger.info(
                'Chrome extension diagnostics, targetCount=%s, extensionPages=%s, extensionWorkers=%s',
                len(targets),
                len(extension_pages),
                len(extension_workers),
            )
        except Exception as exc:
            logger.warning('CDP target diagnostics failed, msg=%s', exc)

    def _quietly_close_browser(self, browser: Browser) -> None:
        try:
            browser.close()
        except Exception:
            pass

    def _quietly_stop_playwright(self, playwright: Playwright) -> None:
        try:
            playwright.stop()
        except Exception:
            pass

    def _quietly_detach_cdp(self, browser_cdp: CDPSession) -> None:
        try:
            browser_cdp.detach()
        except Exception:
            pass


browser_session_manager = BrowserSessionManager()
