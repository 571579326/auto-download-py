from fastapi import APIRouter, Body
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import Result
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
    RpaOpenTabRequest,
    RpaOpenUrlRequest,
    RpaPageReloadRequest,
    RpaPageTarget,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaScreenshotRequest,
    RpaScreenshotResponse,
)
from app.services.rpa.rpa_element_service import rpa_element_service
from app.services.rpa.rpa_locator_service import rpa_locator_service
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


# ----------------------------- element -----------------------------
@router.post('/element/exists', response_model=Result[RpaElementOperationResponse])
async def element_exists(request: RpaElementTextRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.exists, request)
    return Result(message='rpa element exists 成功', data=data)


@router.post('/element/click', response_model=Result[RpaElementOperationResponse])
async def element_click(request: RpaElementClickRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.click, request)
    return Result(message='rpa element click 成功', data=data)


@router.post('/element/input', response_model=Result[RpaElementOperationResponse])
async def element_input(request: RpaElementInputRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.input, request)
    return Result(message='rpa element input 成功', data=data)


@router.post('/element/text', response_model=Result[RpaElementOperationResponse])
async def element_text(request: RpaElementTextRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.text, request)
    return Result(message='rpa element text 成功', data=data)


@router.post('/element/attribute', response_model=Result[RpaElementOperationResponse])
async def element_attribute(request: RpaElementAttributeRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.attribute, request)
    return Result(message='rpa element attribute 成功', data=data)


@router.post('/element/press', response_model=Result[RpaElementOperationResponse])
async def element_press(request: RpaElementPressRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.press, request)
    return Result(message='rpa element press 成功', data=data)


@router.post('/element/select', response_model=Result[RpaElementOperationResponse])
async def element_select(request: RpaElementSelectRequest = Body(...)):
    data = await run_in_threadpool(rpa_element_service.select, request)
    return Result(message='rpa element select 成功', data=data)


# ----------------------------- locator -----------------------------
@router.post('/locator/find', response_model=Result[RpaLocatorFindResponse])
async def locator_find(request: RpaLocatorFindRequest = Body(...)):
    """按 selector/文本/属性/role 等条件查找网页 UI 元素。"""
    data = await run_in_threadpool(rpa_locator_service.find, request)
    return Result(message='rpa locator find 成功', data=data)


@router.post('/locator/describe', response_model=Result[RpaLocatorFindResponse])
async def locator_describe(request: RpaLocatorDescribeRequest = Body(...)):
    """描述 selector 命中的第一个元素。"""
    data = await run_in_threadpool(rpa_locator_service.describe, request)
    return Result(message='rpa locator describe 成功', data=data)


@router.post('/locator/count', response_model=Result[RpaLocatorCountResponse])
async def locator_count(request: RpaLocatorCountRequest = Body(...)):
    """统计 selector 命中数量。"""
    data = await run_in_threadpool(rpa_locator_service.count, request)
    return Result(message='rpa locator count 成功', data=data)
