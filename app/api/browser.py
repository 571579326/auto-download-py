from typing import Annotated

from fastapi import APIRouter, Body, Query
from fastapi.concurrency import run_in_threadpool

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
from app.schemas.common import Result
from app.services.browser_service import browser_service

router = APIRouter(prefix='/browser', tags=['browser'])


def _resolve_window_id(window_id: str | None, session_id: str | None) -> str:
    resolved = (window_id or session_id or '').strip()
    if not resolved:
        raise ValueError('windowId不能为空')
    return resolved


@router.post('/session/open', response_model=Result[OpenWindowResponse])
@router.post('/window/open', response_model=Result[OpenWindowResponse])
async def open_window():
    data = await run_in_threadpool(browser_service.open_browser)
    return Result(message='openWindow 成功', data=data)


@router.post('/session/open-pure', response_model=Result[OpenWindowResponse])
@router.post('/window/open-pure', response_model=Result[OpenWindowResponse])
async def open_window_pure(
    url: Annotated[str | None, Query(description='可选。纯净模式启动后直接打开的URL；为空时按快捷方式打开默认页。')] = None,
    newWindow: Annotated[bool | None, Query(description='可选。是否追加 --new-window；默认不追加，尽量贴近手动快捷方式。')] = None,
):
    data = await run_in_threadpool(browser_service.open_browser_pure, url, newWindow)
    return Result(message='openWindowPure 成功', data=data)


@router.post('/session/open-selenium', response_model=Result[SeleniumOpenWindowResponse])
@router.post('/window/open-selenium', response_model=Result[SeleniumOpenWindowResponse])
async def open_window_selenium(
    url: Annotated[str | None, Query(description='可选。Selenium 附加到 9222 后打开的URL；为空时使用 SELENIUM_BROWSER_START_URL。')] = None,
    newWindow: Annotated[bool | None, Query(description='可选。是否通过 Selenium 新开窗口；为空时使用 SELENIUM_BROWSER_NEW_WINDOW。')] = None,
    ensureBrowser: Annotated[bool, Query(description='可选。9222 未启动时是否先用纯净模式启动 Chrome；默认 true。')] = True,
):
    data = await run_in_threadpool(browser_service.open_browser_selenium, url, newWindow, ensureBrowser)
    return Result(message='openWindowSelenium 成功', data=data)


@router.get('/windows', response_model=Result[WindowListResponse])
async def list_windows():
    data = await run_in_threadpool(browser_service.list_windows)
    return Result(message='listWindows 成功', data=data)


@router.post('/tab/open', response_model=Result[PageInfoResponse])
async def open_tab(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    request: NewTabRequest | None = Body(default=None),
):
    data = await run_in_threadpool(browser_service.new_tab, _resolve_window_id(windowId, sessionId), request)
    return Result(message='openTab 成功', data=data)


@router.post('/page/open-url', response_model=Result[PageInfoResponse])
async def open_url(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    request: OpenUrlRequest = Body(...),
):
    data = await run_in_threadpool(browser_service.open_url, _resolve_window_id(windowId, sessionId), request)
    return Result(message='openUrl 成功', data=data)


@router.post('/page/batch-open-config', response_model=Result[BatchOpenPagesResponse])
async def batch_open_config(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    request: OpenConfiguredPagesRequest = Body(...),
):
    data = await run_in_threadpool(browser_service.open_config_pages, _resolve_window_id(windowId, sessionId), request)
    return Result(message='batchOpenConfig success', data=data)


@router.get('/pages', response_model=Result[PageListResponse])
async def list_pages(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(browser_service.list_pages, _resolve_window_id(windowId, sessionId))
    return Result(message='listPages 成功', data=data)


@router.get('/page-info', response_model=Result[PageInfoResponse])
async def get_page_info(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    pageId: Annotated[str | None, Query()] = None,
    urlContains: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(
        browser_service.get_page_info,
        _resolve_window_id(windowId, sessionId),
        pageId,
        urlContains,
    )
    return Result(message='getPageInfo 成功', data=data)


@router.post('/page/activate', response_model=Result[PageInfoResponse])
async def activate_page(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    pageId: Annotated[str | None, Query()] = None,
    urlContains: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(
        browser_service.activate_page,
        _resolve_window_id(windowId, sessionId),
        pageId,
        urlContains,
    )
    return Result(message='activatePage 成功', data=data)


@router.post('/page/close', response_model=Result[ClosePageResponse])
async def close_page(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    pageId: Annotated[str | None, Query()] = None,
    urlContains: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(
        browser_service.close_page,
        _resolve_window_id(windowId, sessionId),
        pageId,
        urlContains,
    )
    return Result(message='closePage 成功', data=data)


@router.post('/bing-huya', response_model=Result[PageInfoResponse])
async def bing_huya(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    request: BingHuyaRequest | None = Body(default=None),
):
    data = await run_in_threadpool(browser_service.bing_huya, _resolve_window_id(windowId, sessionId), request)
    return Result(message='bingHuya 成功', data=data)


@router.get('/takeover/page-info', response_model=Result[PageInfoResponse])
async def takeover_page_info(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
    pageId: Annotated[str | None, Query()] = None,
    urlContains: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(
        browser_service.takeover_page_info,
        _resolve_window_id(windowId, sessionId),
        pageId,
        urlContains,
    )
    return Result(message='takeoverPageInfo 成功', data=data)


@router.post('/window/reopen', response_model=Result[ReopenWindowResponse])
async def reopen_window(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(browser_service.reopen_window, _resolve_window_id(windowId, sessionId))
    return Result(message='reopenWindow 成功', data=data)


@router.post('/window/invalidate', response_model=Result[InvalidateWindowResponse])
async def invalidate_window(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(browser_service.invalidate_window, _resolve_window_id(windowId, sessionId))
    return Result(message='invalidateWindow 成功', data=data)


@router.post('/close', response_model=Result[InvalidateWindowResponse])
async def close_window(
    windowId: Annotated[str | None, Query()] = None,
    sessionId: Annotated[str | None, Query()] = None,
):
    data = await run_in_threadpool(browser_service.close_browser, _resolve_window_id(windowId, sessionId))
    return Result(message='closeWindow 成功', data=data)
