import logging
import time
from typing import Any, Callable

from pydantic import BaseModel

from app.schemas.rpa import (
    RpaElementAttributeRequest,
    RpaElementClickRequest,
    RpaElementInputRequest,
    RpaElementPressRequest,
    RpaElementSelectRequest,
    RpaElementTextRequest,
    RpaLocatorCountRequest,
    RpaLocatorDescribeRequest,
    RpaLocatorFindRequest,
    RpaDataCleanRequest,
    RpaDataExtractRegexRequest,
    RpaDataFileReadRequest,
    RpaDataFileWriteRequest,
    RpaDataFilterRequest,
    RpaDataGroupCountRequest,
    RpaDataSortRequest,
    RpaDataUniqueRequest,
    RpaFlowRunRequest,
    RpaFlowRunResponse,
    RpaFlowStep,
    RpaFlowStepResult,
    RpaImageClickManyRequest,
    RpaImageClickRequest,
    RpaImageLocateRequest,
    RpaKeyboardHotkeyRequest,
    RpaKeyboardPressRequest,
    RpaKeyboardTypeRequest,
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
    RpaWaitSleepRequest,
)
from app.schemas.rpa import RpaClipboardSetRequest
from app.services.rpa.rpa_assert_service import rpa_assert_service
from app.services.rpa.rpa_clipboard_service import rpa_clipboard_service
from app.services.rpa.rpa_element_service import rpa_element_service
from app.services.rpa.rpa_image_service import rpa_image_service
from app.services.rpa.rpa_keyboard_service import rpa_keyboard_service
from app.services.rpa.rpa_locator_service import rpa_locator_service
from app.services.rpa.rpa_data_service import rpa_data_service
from app.services.rpa.rpa_mouse_service import rpa_mouse_service
from app.services.rpa.rpa_page_service import rpa_page_service
from app.services.rpa.rpa_wait_service import rpa_wait_service

logger = logging.getLogger(__name__)


class RpaFlowService:
    """RPA 流程编排公共方法层。

    该类把分类动作组合成可配置流程，适合替代影刀中“拖动作块”的日常用法。
    请求体里的每个 step 都是一个动作，params 就是该动作对应请求模型的字段。
    """

    def run(self, request: RpaFlowRunRequest) -> RpaFlowRunResponse:
        """顺序执行流程步骤。

        - step.retryTimes 控制失败重试；
        - step.continueOnError 为 true 时失败后继续执行后续步骤；
        - 顶层 windowId 会自动补到缺少 windowId 的步骤 params 中。
        """
        results: list[RpaFlowStepResult] = []
        stopped_at: int | None = None

        for index, step in enumerate(request.steps, start=1):
            step_params = dict(step.params or {})
            if request.windowId and 'windowId' not in step_params:
                step_params['windowId'] = request.windowId

            success = False
            data: Any | None = None
            error: str | None = None
            attempts = 0

            max_attempts = step.retryTimes + 1
            for attempt_index in range(1, max_attempts + 1):
                attempts = attempt_index
                try:
                    data = self._execute_step(step, step_params)
                    success = True
                    error = None
                    break
                except Exception as exc:
                    error = str(exc)
                    logger.warning(
                        'RPA流程步骤失败, index=%s, action=%s, attempt=%s/%s, error=%s',
                        index,
                        step.action,
                        attempt_index,
                        max_attempts,
                        exc,
                    )
                    if attempt_index < max_attempts and step.retryIntervalSeconds > 0:
                        time.sleep(step.retryIntervalSeconds)

            results.append(
                RpaFlowStepResult(
                    index=index,
                    name=step.name,
                    action=step.action,
                    success=success,
                    attempts=attempts,
                    data=self._dump_data(data),
                    error=error,
                )
            )

            if not success and not step.continueOnError:
                stopped_at = index
                break

        success_count = sum(1 for item in results if item.success)
        failed_count = sum(1 for item in results if not item.success)
        return RpaFlowRunResponse(
            success=failed_count == 0,
            total=len(request.steps),
            successCount=success_count,
            failedCount=failed_count,
            stoppedAt=stopped_at,
            steps=results,
        )

    def _execute_step(self, step: RpaFlowStep, params: dict[str, Any]) -> Any:
        """把 action 名称路由到具体公共方法。"""
        action = step.action.strip().lower().replace('-', '_')
        actions: dict[str, Callable[[dict[str, Any]], Any]] = {
            'page.reconnect': lambda p: rpa_page_service.reconnect(RpaPageTarget(**p)),
            'page.info': lambda p: rpa_page_service.info(RpaPageTarget(**p)),
            'page.list': lambda p: rpa_page_service.list_pages(RpaPageTarget(**p)),
            'page.activate': lambda p: rpa_page_service.activate(RpaPageTarget(**p)),
            'page.open_tab': lambda p: rpa_page_service.open_tab(RpaOpenTabRequest(**p)),
            'page.open_url': lambda p: rpa_page_service.open_url(RpaOpenUrlRequest(**p)),
            'page.reload': lambda p: rpa_page_service.reload(RpaPageReloadRequest(**p)),
            'page.wait_load_state': lambda p: rpa_page_service.wait_load_state(RpaPageWaitLoadStateRequest(**p)),
            'page.wait_url_contains': lambda p: rpa_page_service.wait_url_contains(RpaPageWaitUrlRequest(**p)),
            'page.screenshot': lambda p: rpa_page_service.screenshot(RpaScreenshotRequest(**p)),
            'element.exists': lambda p: rpa_element_service.exists(RpaElementTextRequest(**p)),
            'element.click': lambda p: rpa_element_service.click(RpaElementClickRequest(**p)),
            'element.input': lambda p: rpa_element_service.input(RpaElementInputRequest(**p)),
            'element.text': lambda p: rpa_element_service.text(RpaElementTextRequest(**p)),
            'element.attribute': lambda p: rpa_element_service.attribute(RpaElementAttributeRequest(**p)),
            'element.press': lambda p: rpa_element_service.press(RpaElementPressRequest(**p)),
            'element.select': lambda p: rpa_element_service.select(RpaElementSelectRequest(**p)),
            'locator.find': lambda p: rpa_locator_service.find(RpaLocatorFindRequest(**p)),
            'locator.describe': lambda p: rpa_locator_service.describe(RpaLocatorDescribeRequest(**p)),
            'locator.count': lambda p: rpa_locator_service.count(RpaLocatorCountRequest(**p)),
            'image.locate': lambda p: rpa_image_service.locate(RpaImageLocateRequest(**p)),
            'image.wait': lambda p: rpa_image_service.wait(RpaImageLocateRequest(**p)),
            'image.click': lambda p: rpa_image_service.click(RpaImageClickRequest(**p)),
            'image.click_many': lambda p: rpa_image_service.click_many(RpaImageClickManyRequest(**p)),
            'data.clean': lambda p: rpa_data_service.clean_rows(RpaDataCleanRequest(**p)),
            'data.filter': lambda p: rpa_data_service.filter_rows(RpaDataFilterRequest(**p)),
            'data.sort': lambda p: rpa_data_service.sort_rows(RpaDataSortRequest(**p)),
            'data.unique': lambda p: rpa_data_service.unique_rows(RpaDataUniqueRequest(**p)),
            'data.group_count': lambda p: rpa_data_service.group_count(RpaDataGroupCountRequest(**p)),
            'data.extract_regex': lambda p: rpa_data_service.extract_regex(RpaDataExtractRegexRequest(**p)),
            'data.read_file': lambda p: rpa_data_service.read_file(RpaDataFileReadRequest(**p)),
            'data.write_file': lambda p: rpa_data_service.write_file(RpaDataFileWriteRequest(**p)),
            'mouse.click': lambda p: rpa_mouse_service.click(RpaMouseClickRequest(**p)),
            'mouse.move': lambda p: rpa_mouse_service.move(RpaMouseMoveRequest(**p)),
            'mouse.drag': lambda p: rpa_mouse_service.drag(RpaMouseDragRequest(**p)),
            'mouse.scroll': lambda p: rpa_mouse_service.scroll(RpaMouseScrollRequest(**p)),
            'keyboard.type': lambda p: rpa_keyboard_service.type_text(RpaKeyboardTypeRequest(**p)),
            'keyboard.hotkey': lambda p: rpa_keyboard_service.hotkey(RpaKeyboardHotkeyRequest(**p)),
            'keyboard.press': lambda p: rpa_keyboard_service.press(RpaKeyboardPressRequest(**p)),
            'clipboard.set': lambda p: rpa_clipboard_service.set_text(RpaClipboardSetRequest(**p)),
            'clipboard.get': lambda p: rpa_clipboard_service.get_text(),
            'clipboard.paste': lambda p: rpa_clipboard_service.paste(),
            'wait.sleep': lambda p: rpa_wait_service.sleep(RpaWaitSleepRequest(**p)),
            'wait.element': lambda p: rpa_wait_service.element_exists(RpaElementTextRequest(**p)),
            'wait.image': lambda p: rpa_wait_service.image_exists(RpaImageLocateRequest(**p)),
            'wait.url_contains': lambda p: rpa_wait_service.url_contains(RpaPageWaitUrlRequest(**p)),
            'assert.element_exists': lambda p: rpa_assert_service.element_exists(RpaElementTextRequest(**p)),
            'assert.image_exists': lambda p: rpa_assert_service.image_exists(RpaImageLocateRequest(**p)),
            'assert.url_contains': self._assert_url_contains,
            'assert.text_contains': self._assert_text_contains,
        }
        executor = actions.get(action)
        if executor is None:
            raise ValueError(f'不支持的RPA动作: {step.action}')
        return executor(params)

    @staticmethod
    def _assert_url_contains(params: dict[str, Any]) -> Any:
        expected = params.pop('expected', None) or params.pop('text', None) or params.pop('urlContainsTarget', None)
        if not expected:
            raise ValueError('assert.url_contains 需要 expected/text/urlContainsTarget 参数')
        return rpa_assert_service.url_contains(RpaPageTarget(**params), str(expected))

    @staticmethod
    def _assert_text_contains(params: dict[str, Any]) -> Any:
        expected = params.pop('expected', None) or params.pop('textExpected', None)
        if expected is None:
            raise ValueError('assert.text_contains 需要 expected/textExpected 参数')
        return rpa_assert_service.text_contains(RpaElementTextRequest(**params), str(expected))

    @staticmethod
    def _dump_data(data: Any) -> Any:
        """把 pydantic 响应转换为可 JSON 序列化对象。"""
        if isinstance(data, BaseModel):
            return data.model_dump()
        if isinstance(data, list):
            return [RpaFlowService._dump_data(item) for item in data]
        if isinstance(data, dict):
            return {key: RpaFlowService._dump_data(value) for key, value in data.items()}
        return data


rpa_flow_service = RpaFlowService()
