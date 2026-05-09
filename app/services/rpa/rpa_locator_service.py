from app.schemas.rpa import (
    RpaLocatorCountRequest,
    RpaLocatorCountResponse,
    RpaLocatorDescribeRequest,
    RpaLocatorFindRequest,
    RpaLocatorFindResponse,
)
from app.services.browser_service import browser_service


class RpaLocatorService:
    """RPA 网页 UI 元素定位公共方法层。

    这里对应影刀 RPA 中“捕获网页元素/查找网页元素”的基础能力。
    它不直接执行业务点击，而是先把页面上的候选元素、推荐 selector、文本、属性、坐标等信息找出来，
    后续再交给 element.click/input/text 等动作复用。
    """

    def find(self, request: RpaLocatorFindRequest) -> RpaLocatorFindResponse:
        """按 selector、文本、标签、属性、role 等条件查找网页 UI 元素。"""
        return browser_service.rpa_locator_find(request)

    def describe(self, request: RpaLocatorDescribeRequest) -> RpaLocatorFindResponse:
        """描述单个 selector 命中的元素，返回推荐定位器和基础属性。"""
        return browser_service.rpa_locator_describe(request)

    def count(self, request: RpaLocatorCountRequest) -> RpaLocatorCountResponse:
        """统计 selector 命中的元素数量，可选只统计可见元素。"""
        return browser_service.rpa_locator_count(request)


rpa_locator_service = RpaLocatorService()
