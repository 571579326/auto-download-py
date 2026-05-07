from typing import Annotated

from fastapi import APIRouter, Body, Query
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import Result
from app.schemas.desktop import (
    ActivateWindowRequest,
    ActivateWindowResponse,
    ClickImageRequest,
    ClickImageResponse,
    ClickPositionRequest,
    ClickPositionResponse,
    HotkeyRequest,
    KeyboardActionResponse,
    OcrClickTextRequest,
    OcrClickTextResponse,
    TypeTextRequest,
    WindowListResponse,
    WindowQueryRequest,
)
from app.services.desktop_service import desktop_service
from app.services.visual_service import visual_service

router = APIRouter(prefix='/desktop', tags=['desktop'])


@router.get('/windows', response_model=Result[WindowListResponse])
async def list_windows(
    backend: Annotated[str, Query()] = 'uia',
    titleContains: Annotated[str | None, Query()] = None,
    titleRegex: Annotated[str | None, Query()] = None,
    onlyVisible: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query()] = 50,
):
    request = WindowQueryRequest(
        backend=backend,
        titleContains=titleContains,
        titleRegex=titleRegex,
        onlyVisible=onlyVisible,
        limit=limit,
    )
    data = await run_in_threadpool(desktop_service.list_windows, request)
    return Result(message='listWindows 成功', data=data)


@router.post('/window/activate', response_model=Result[ActivateWindowResponse])
async def activate_window(request: ActivateWindowRequest = Body(...)):
    data = await run_in_threadpool(desktop_service.activate_window, request)
    return Result(message='activateWindow 成功', data=data)


@router.post('/click/pos', response_model=Result[ClickPositionResponse])
async def click_position(request: ClickPositionRequest = Body(...)):
    data = await run_in_threadpool(visual_service.click_position, request)
    return Result(message='clickPosition 成功', data=data)


@router.post('/click/image', response_model=Result[ClickImageResponse])
async def click_image(request: ClickImageRequest = Body(...)):
    data = await run_in_threadpool(visual_service.click_image, request)
    return Result(message='clickImage 成功', data=data)


@router.post('/click/ocr-text', response_model=Result[OcrClickTextResponse])
async def click_ocr_text(request: OcrClickTextRequest = Body(...)):
    data = await run_in_threadpool(visual_service.ocr_click_text_reserved, request)
    return Result(message='clickOcrText 预留接口返回成功', data=data)


@router.post('/keyboard/type', response_model=Result[KeyboardActionResponse])
async def type_text(request: TypeTextRequest = Body(...)):
    data = await run_in_threadpool(desktop_service.type_text, request)
    return Result(message='typeText 成功', data=data)


@router.post('/keyboard/hotkey', response_model=Result[KeyboardActionResponse])
async def hotkey(request: HotkeyRequest = Body(...)):
    data = await run_in_threadpool(desktop_service.hotkey, request)
    return Result(message='hotkey 成功', data=data)
