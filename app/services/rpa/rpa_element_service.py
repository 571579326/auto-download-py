from app.schemas.rpa import (
    RpaElementAttributeRequest,
    RpaElementClickRequest,
    RpaElementInputRequest,
    RpaElementOperationResponse,
    RpaElementPressRequest,
    RpaElementSelectRequest,
    RpaElementTextRequest,
)
from app.services.browser_service import browser_service


class RpaElementService:
    """RPA DOM 元素公共方法层。

    面向网页元素的操作都放在这里，底层由 Playwright/CDP 接管页面后执行。
    适合能稳定拿到 selector 的页面；拿不到 selector 时再走图像/坐标操作。
    """

    def exists(self, request: RpaElementTextRequest) -> RpaElementOperationResponse:
        """判断元素是否存在，不存在时不会抛错。"""
        return browser_service.rpa_element_exists(request)

    def click(self, request: RpaElementClickRequest) -> RpaElementOperationResponse:
        """点击 DOM 元素。"""
        return browser_service.rpa_element_click(request)

    def input(self, request: RpaElementInputRequest) -> RpaElementOperationResponse:
        """输入文本到 DOM 元素。"""
        return browser_service.rpa_element_input(request)

    def text(self, request: RpaElementTextRequest) -> RpaElementOperationResponse:
        """读取 DOM 元素文本。"""
        return browser_service.rpa_element_text(request)

    def attribute(self, request: RpaElementAttributeRequest) -> RpaElementOperationResponse:
        """读取 DOM 元素属性。"""
        return browser_service.rpa_element_attribute(request)

    def press(self, request: RpaElementPressRequest) -> RpaElementOperationResponse:
        """在 DOM 元素上执行按键。"""
        return browser_service.rpa_element_press(request)

    def select(self, request: RpaElementSelectRequest) -> RpaElementOperationResponse:
        """选择 select 下拉框 option。"""
        return browser_service.rpa_element_select(request)


rpa_element_service = RpaElementService()
