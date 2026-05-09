from fastapi import APIRouter, Body
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import Result
from app.schemas.rpa import (
    RpaOpenTabRequest,
    RpaOpenUrlRequest,
    RpaPageReloadRequest,
    RpaPageTarget,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaScreenshotRequest,
    RpaScreenshotResponse,
)
from app.services.rpa.rpa_page_service import rpa_page_service

router = APIRouter(prefix='/rpa', tags=['rpa'])


# ----------------------------- page -----------------------------
@router.post('/page/reconnect')
async def reconnect_page(request: RpaPageTarget = Body(...)):
    """重连/接管已有页面。"""
    data = await run_in_threadpool(rpa_page_service.reconnect, request)
    return Result(message='rpa page reconnect 成功', data=data)


@router.post('/page/info')
async def page_info(request: RpaPageTarget = Body(...)):
    """读取页面信息。"""
    data = await run_in_threadpool(rpa_page_service.info, request)
    return Result(message='rpa page info 成功', data=data)


@router.post('/page/list')
async def list_pages(request: RpaPageTarget = Body(...)):
    """列出窗口页面。"""
    data = await run_in_threadpool(rpa_page_service.list_pages, request)
    return Result(message='rpa page list 成功', data=data)


@router.post('/page/activate')
async def activate_page(request: RpaPageTarget = Body(...)):
    """激活目标页面。"""
    data = await run_in_threadpool(rpa_page_service.activate, request)
    return Result(message='rpa page activate 成功', data=data)


@router.post('/page/open-tab')
async def open_tab(request: RpaOpenTabRequest = Body(...)):
    """打开新标签页。"""
    data = await run_in_threadpool(rpa_page_service.open_tab, request)
    return Result(message='rpa page openTab 成功', data=data)


@router.post('/page/open-url')
async def open_url(request: RpaOpenUrlRequest = Body(...)):
    """打开 URL。"""
    data = await run_in_threadpool(rpa_page_service.open_url, request)
    return Result(message='rpa page openUrl 成功', data=data)


@router.post('/page/reload')
async def reload_page(request: RpaPageReloadRequest = Body(...)):
    """刷新页面。"""
    data = await run_in_threadpool(rpa_page_service.reload, request)
    return Result(message='rpa page reload 成功', data=data)


@router.post('/page/wait-load-state')
async def wait_load_state(request: RpaPageWaitLoadStateRequest = Body(...)):
    """等待页面加载状态。"""
    data = await run_in_threadpool(rpa_page_service.wait_load_state, request)
    return Result(message='rpa page waitLoadState 成功', data=data)


@router.post('/page/wait-url')
async def wait_url(request: RpaPageWaitUrlRequest = Body(...)):
    """等待 URL 包含关键字。"""
    data = await run_in_threadpool(rpa_page_service.wait_url_contains, request)
    return Result(message='rpa page waitUrl 成功', data=data)


@router.post('/page/screenshot', response_model=Result[RpaScreenshotResponse])
async def page_screenshot(request: RpaScreenshotRequest = Body(...)):
    """页面截图。"""
    data = await run_in_threadpool(rpa_page_service.screenshot, request)
    return Result(message='rpa page screenshot 成功', data=data)
