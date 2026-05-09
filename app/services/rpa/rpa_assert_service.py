from app.schemas.rpa import RpaAssertResponse, RpaElementTextRequest, RpaImageLocateRequest, RpaPageTarget
from app.services.rpa.rpa_element_service import rpa_element_service
from app.services.rpa.rpa_image_service import rpa_image_service
from app.services.rpa.rpa_page_service import rpa_page_service


class RpaAssertService:
    """RPA 断言公共方法层。

    断言用于流程中判断当前状态是否符合预期；断言失败时默认抛错，方便 flow 停止并返回失败步骤。
    """

    def url_contains(self, request: RpaPageTarget, expected: str) -> RpaAssertResponse:
        """断言当前页面 URL 包含指定关键字。"""
        page_info = rpa_page_service.info(request)
        passed = expected in (page_info.url or '')
        if not passed:
            raise RuntimeError(f'URL断言失败: expected contains {expected}, actual={page_info.url}')
        return RpaAssertResponse(passed=True, message='URL断言通过', actual=page_info.url)

    def element_exists(self, request: RpaElementTextRequest) -> RpaAssertResponse:
        """断言 DOM 元素存在。"""
        result = rpa_element_service.exists(request)
        if not result.exists:
            raise RuntimeError(f'元素存在断言失败: {request.selector}')
        return RpaAssertResponse(passed=True, message='元素存在断言通过', actual=request.selector)

    def text_contains(self, request: RpaElementTextRequest, expected: str) -> RpaAssertResponse:
        """断言 DOM 元素文本包含指定内容。"""
        result = rpa_element_service.text(request)
        actual = result.text or ''
        if expected not in actual:
            raise RuntimeError(f'文本断言失败: expected contains {expected}, actual={actual}')
        return RpaAssertResponse(passed=True, message='文本断言通过', actual=actual)

    def image_exists(self, request: RpaImageLocateRequest) -> RpaAssertResponse:
        """断言图像存在。"""
        result = rpa_image_service.locate(request)
        if not result.found:
            raise RuntimeError(f'图像存在断言失败: {request.imagePath}, error={result.error}')
        return RpaAssertResponse(passed=True, message='图像存在断言通过', actual=result.model_dump())


rpa_assert_service = RpaAssertService()
