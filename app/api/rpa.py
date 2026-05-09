from fastapi import APIRouter, Body
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import Result
from app.schemas.rpa import (
    RpaAssertResponse,
    RpaClipboardResponse,
    RpaClipboardSetRequest,
    RpaDataCleanRequest,
    RpaDataExtractRegexRequest,
    RpaDataFileReadRequest,
    RpaDataFileWriteRequest,
    RpaDataFilterRequest,
    RpaDataGroupCountRequest,
    RpaDataSortRequest,
    RpaDataTableResponse,
    RpaDataUniqueRequest,
    RpaDataValueResponse,
    RpaElementAttributeRequest,
    RpaElementClickRequest,
    RpaElementInputRequest,
    RpaElementOperationResponse,
    RpaElementPressRequest,
    RpaElementSelectRequest,
    RpaElementTextRequest,
    RpaFlowRunRequest,
    RpaFlowRunResponse,
    RpaImageClickManyRequest,
    RpaImageClickRequest,
    RpaImageLocateRequest,
    RpaImageLocateResponse,
    RpaKeyboardActionResponse,
    RpaKeyboardHotkeyRequest,
    RpaKeyboardPressRequest,
    RpaKeyboardTypeRequest,
    RpaLocatorCountRequest,
    RpaLocatorCountResponse,
    RpaLocatorDescribeRequest,
    RpaLocatorFindRequest,
    RpaLocatorFindResponse,
    RpaMouseActionResponse,
    RpaMouseClickRequest,
    RpaMouseDragRequest,
    RpaMouseMoveRequest,
    RpaMouseScrollRequest,
    RpaOpenTabRequest,
    RpaOpenUrlRequest,
    RpaPageReloadRequest,
    RpaPageTarget,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaScreenshotRequest,
    RpaScreenshotResponse,
    RpaWaitSleepRequest,
)
from app.services.rpa.rpa_assert_service import rpa_assert_service
from app.services.rpa.rpa_clipboard_service import rpa_clipboard_service
from app.services.rpa.rpa_data_service import rpa_data_service
from app.services.rpa.rpa_element_service import rpa_element_service
from app.services.rpa.rpa_flow_service import rpa_flow_service
from app.services.rpa.rpa_image_service import rpa_image_service
from app.services.rpa.rpa_keyboard_service import rpa_keyboard_service
from app.services.rpa.rpa_locator_service import rpa_locator_service
from app.services.rpa.rpa_mouse_service import rpa_mouse_service
from app.services.rpa.rpa_page_service import rpa_page_service
from app.services.rpa.rpa_wait_service import rpa_wait_service

router = APIRouter(prefix='/rpa', tags=['rpa'])


# ----------------------------- page -----------------------------
@router.post('/page/reconnect')
async def reconnect_page(request: RpaPageTarget = Body(...)):
    data = await run_in_threadpool(rpa_page_service.reconnect, request)
    return Result(message='rpa page reconnect 成功', data=data)


@router.post('/page/info')
async def page_info(request: RpaPageTarget = Body(...)):
    data = await run_in_threadpool(rpa_page_service.info, request)
    return Result(message='rpa page info 成功', data=data)


@router.post('/page/list')
async def list_pages(request: RpaPageTarget = Body(...)):
    data = await run_in_threadpool(rpa_page_service.list_pages, request)
    return Result(message='rpa page list 成功', data=data)


@router.post('/page/activate')
async def activate_page(request: RpaPageTarget = Body(...)):
    data = await run_in_threadpool(rpa_page_service.activate, request)
    return Result(message='rpa page activate 成功', data=data)


@router.post('/page/open-tab')
async def open_tab(request: RpaOpenTabRequest = Body(...)):
    data = await run_in_threadpool(rpa_page_service.open_tab, request)
    return Result(message='rpa page openTab 成功', data=data)


@router.post('/page/open-url')
async def open_url(request: RpaOpenUrlRequest = Body(...)):
    data = await run_in_threadpool(rpa_page_service.open_url, request)
    return Result(message='rpa page openUrl 成功', data=data)


@router.post('/page/reload')
async def reload_page(request: RpaPageReloadRequest = Body(...)):
    data = await run_in_threadpool(rpa_page_service.reload, request)
    return Result(message='rpa page reload 成功', data=data)


@router.post('/page/wait-load-state')
async def wait_load_state(request: RpaPageWaitLoadStateRequest = Body(...)):
    data = await run_in_threadpool(rpa_page_service.wait_load_state, request)
    return Result(message='rpa page waitLoadState 成功', data=data)


@router.post('/page/wait-url')
async def wait_url(request: RpaPageWaitUrlRequest = Body(...)):
    data = await run_in_threadpool(rpa_page_service.wait_url_contains, request)
    return Result(message='rpa page waitUrl 成功', data=data)


@router.post('/page/screenshot', response_model=Result[RpaScreenshotResponse])
async def page_screenshot(request: RpaScreenshotRequest = Body(...)):
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
    data = await run_in_threadpool(rpa_locator_service.find, request)
    return Result(message='rpa locator find 成功', data=data)


@router.post('/locator/describe', response_model=Result[RpaLocatorFindResponse])
async def locator_describe(request: RpaLocatorDescribeRequest = Body(...)):
    data = await run_in_threadpool(rpa_locator_service.describe, request)
    return Result(message='rpa locator describe 成功', data=data)


@router.post('/locator/count', response_model=Result[RpaLocatorCountResponse])
async def locator_count(request: RpaLocatorCountRequest = Body(...)):
    data = await run_in_threadpool(rpa_locator_service.count, request)
    return Result(message='rpa locator count 成功', data=data)


# ----------------------------- image -----------------------------
@router.post('/image/locate', response_model=Result[RpaImageLocateResponse])
async def image_locate(request: RpaImageLocateRequest = Body(...)):
    data = await run_in_threadpool(rpa_image_service.locate, request)
    return Result(message='rpa image locate 成功', data=data)


@router.post('/image/wait', response_model=Result[RpaImageLocateResponse])
async def image_wait(request: RpaImageLocateRequest = Body(...)):
    data = await run_in_threadpool(rpa_image_service.wait, request)
    return Result(message='rpa image wait 成功', data=data)


@router.post('/image/click')
async def image_click(request: RpaImageClickRequest = Body(...)):
    data = await run_in_threadpool(rpa_image_service.click, request)
    return Result(message='rpa image click 成功', data=data)


@router.post('/image/click-many')
async def image_click_many(request: RpaImageClickManyRequest = Body(...)):
    data = await run_in_threadpool(rpa_image_service.click_many, request)
    return Result(message='rpa image clickMany 成功', data=data)


# ----------------------------- mouse -----------------------------
@router.post('/mouse/click', response_model=Result[RpaMouseActionResponse])
async def mouse_click(request: RpaMouseClickRequest = Body(...)):
    data = await run_in_threadpool(rpa_mouse_service.click, request)
    return Result(message='rpa mouse click 成功', data=data)


@router.post('/mouse/move', response_model=Result[RpaMouseActionResponse])
async def mouse_move(request: RpaMouseMoveRequest = Body(...)):
    data = await run_in_threadpool(rpa_mouse_service.move, request)
    return Result(message='rpa mouse move 成功', data=data)


@router.post('/mouse/drag', response_model=Result[RpaMouseActionResponse])
async def mouse_drag(request: RpaMouseDragRequest = Body(...)):
    data = await run_in_threadpool(rpa_mouse_service.drag, request)
    return Result(message='rpa mouse drag 成功', data=data)


@router.post('/mouse/scroll', response_model=Result[RpaMouseActionResponse])
async def mouse_scroll(request: RpaMouseScrollRequest = Body(...)):
    data = await run_in_threadpool(rpa_mouse_service.scroll, request)
    return Result(message='rpa mouse scroll 成功', data=data)


# ----------------------------- keyboard -----------------------------
@router.post('/keyboard/type', response_model=Result[RpaKeyboardActionResponse])
async def keyboard_type(request: RpaKeyboardTypeRequest = Body(...)):
    data = await run_in_threadpool(rpa_keyboard_service.type_text, request)
    return Result(message='rpa keyboard type 成功', data=data)


@router.post('/keyboard/hotkey', response_model=Result[RpaKeyboardActionResponse])
async def keyboard_hotkey(request: RpaKeyboardHotkeyRequest = Body(...)):
    data = await run_in_threadpool(rpa_keyboard_service.hotkey, request)
    return Result(message='rpa keyboard hotkey 成功', data=data)


@router.post('/keyboard/press', response_model=Result[RpaKeyboardActionResponse])
async def keyboard_press(request: RpaKeyboardPressRequest = Body(...)):
    data = await run_in_threadpool(rpa_keyboard_service.press, request)
    return Result(message='rpa keyboard press 成功', data=data)


# ----------------------------- clipboard -----------------------------
@router.post('/clipboard/set')
async def clipboard_set(request: RpaClipboardSetRequest = Body(...)):
    data = await run_in_threadpool(rpa_clipboard_service.set_text, request)
    return Result(message='rpa clipboard set 成功', data=data)


@router.post('/clipboard/get', response_model=Result[RpaClipboardResponse])
async def clipboard_get():
    data = await run_in_threadpool(rpa_clipboard_service.get_text)
    return Result(message='rpa clipboard get 成功', data=data)


@router.post('/clipboard/paste')
async def clipboard_paste():
    data = await run_in_threadpool(rpa_clipboard_service.paste)
    return Result(message='rpa clipboard paste 成功', data=data)


# ----------------------------- data -----------------------------
@router.post('/data/clean', response_model=Result[RpaDataTableResponse])
async def data_clean(request: RpaDataCleanRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.clean_rows, request)
    return Result(message='rpa data clean 成功', data=data)


@router.post('/data/filter', response_model=Result[RpaDataTableResponse])
async def data_filter(request: RpaDataFilterRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.filter_rows, request)
    return Result(message='rpa data filter 成功', data=data)


@router.post('/data/sort', response_model=Result[RpaDataTableResponse])
async def data_sort(request: RpaDataSortRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.sort_rows, request)
    return Result(message='rpa data sort 成功', data=data)


@router.post('/data/unique', response_model=Result[RpaDataTableResponse])
async def data_unique(request: RpaDataUniqueRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.unique_rows, request)
    return Result(message='rpa data unique 成功', data=data)


@router.post('/data/group-count', response_model=Result[RpaDataValueResponse])
async def data_group_count(request: RpaDataGroupCountRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.group_count, request)
    return Result(message='rpa data groupCount 成功', data=data)


@router.post('/data/extract-regex', response_model=Result[RpaDataTableResponse])
async def data_extract_regex(request: RpaDataExtractRegexRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.extract_regex, request)
    return Result(message='rpa data extractRegex 成功', data=data)


@router.post('/data/read-file', response_model=Result[RpaDataTableResponse])
async def data_read_file(request: RpaDataFileReadRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.read_file, request)
    return Result(message='rpa data readFile 成功', data=data)


@router.post('/data/write-file', response_model=Result[RpaDataValueResponse])
async def data_write_file(request: RpaDataFileWriteRequest = Body(...)):
    data = await run_in_threadpool(rpa_data_service.write_file, request)
    return Result(message='rpa data writeFile 成功', data=data)


# ----------------------------- wait -----------------------------
@router.post('/wait/sleep')
async def wait_sleep(request: RpaWaitSleepRequest = Body(...)):
    data = await run_in_threadpool(rpa_wait_service.sleep, request)
    return Result(message='rpa wait sleep 成功', data=data)


@router.post('/wait/element')
async def wait_element(request: RpaElementTextRequest = Body(...)):
    data = await run_in_threadpool(rpa_wait_service.element_exists, request)
    return Result(message='rpa wait element 成功', data=data)


@router.post('/wait/image')
async def wait_image(request: RpaImageLocateRequest = Body(...)):
    data = await run_in_threadpool(rpa_wait_service.image_exists, request)
    return Result(message='rpa wait image 成功', data=data)


@router.post('/wait/url')
async def wait_url(request: RpaPageWaitUrlRequest = Body(...)):
    data = await run_in_threadpool(rpa_wait_service.url_contains, request)
    return Result(message='rpa wait url 成功', data=data)


# ----------------------------- assert -----------------------------
@router.post('/assert/url-contains', response_model=Result[RpaAssertResponse])
async def assert_url_contains(request: RpaPageWaitUrlRequest = Body(...)):
    data = await run_in_threadpool(rpa_assert_service.url_contains, request)
    return Result(message='rpa assert urlContains 成功', data=data)


@router.post('/assert/element-exists', response_model=Result[RpaAssertResponse])
async def assert_element_exists(request: RpaElementTextRequest = Body(...)):
    data = await run_in_threadpool(rpa_assert_service.element_exists, request)
    return Result(message='rpa assert elementExists 成功', data=data)


@router.post('/assert/image-exists', response_model=Result[RpaAssertResponse])
async def assert_image_exists(request: RpaImageLocateRequest = Body(...)):
    data = await run_in_threadpool(rpa_assert_service.image_exists, request)
    return Result(message='rpa assert imageExists 成功', data=data)


@router.post('/assert/text-contains', response_model=Result[RpaAssertResponse])
async def assert_text_contains(request: RpaElementTextRequest = Body(...)):
    data = await run_in_threadpool(rpa_assert_service.text_contains, request)
    return Result(message='rpa assert textContains 成功', data=data)


# ----------------------------- flow -----------------------------
@router.post('/flow/run', response_model=Result[RpaFlowRunResponse])
async def flow_run(request: RpaFlowRunRequest = Body(...)):
    data = await run_in_threadpool(rpa_flow_service.run, request)
    return Result(message='rpa flow run 成功', data=data)
