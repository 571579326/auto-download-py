from app.schemas.browser import NewTabRequest, OpenUrlRequest, PageInfoResponse, PageListResponse
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
from app.services.browser_service import browser_service


class RpaPageService:
    """RPA 页面公共方法层。

    该类负责浏览器窗口和页面级动作，例如重连、切页、打开 URL、刷新、截图、等待加载。
    业务代码不要直接调用 browser_service 的细节方法，优先通过这里统一入口复用。
    """

    def reconnect(self, request: RpaPageTarget) -> PageInfoResponse:
        """重连/接管已有页面。

        常用于用户手动打开页面后，RPA 流程继续分析或执行点击。
        """
        return browser_service.rpa_reconnect_page(request.windowId, request.pageId, request.urlContains)

    def info(self, request: RpaPageTarget) -> PageInfoResponse:
        """读取目标页面最新信息，并在必要时短接管当前页面。"""
        return browser_service.rpa_reconnect_page(request.windowId, request.pageId, request.urlContains)

    def list_pages(self, request: RpaPageTarget) -> PageListResponse:
        """列出窗口下已记录的页面。"""
        return browser_service.list_pages(request.windowId)

    def activate(self, request: RpaPageTarget) -> PageInfoResponse:
        """激活目标页面，使其成为当前前台页。"""
        return browser_service.activate_page(request.windowId, request.pageId, request.urlContains)

    def open_tab(self, request: RpaOpenTabRequest) -> PageInfoResponse:
        """打开新标签页。"""
        return browser_service.new_tab(
            request.windowId,
            NewTabRequest(url=request.url, bringToFront=request.bringToFront),
        )

    def open_url(self, request: RpaOpenUrlRequest) -> PageInfoResponse:
        """在当前页或新标签页打开 URL。"""
        return browser_service.open_url(
            request.windowId,
            OpenUrlRequest(
                url=request.url,
                pageId=request.pageId,
                urlContains=request.urlContains,
                newTab=request.newTab,
                bringToFront=request.bringToFront,
            ),
        )

    def reload(self, request: RpaPageReloadRequest) -> PageInfoResponse:
        """刷新目标页面。"""
        return browser_service.rpa_reload_page(request)

    def wait_load_state(self, request: RpaPageWaitLoadStateRequest) -> PageInfoResponse:
        """等待页面加载到指定状态。"""
        return browser_service.rpa_wait_load_state(request)

    def wait_url_contains(self, request: RpaPageWaitUrlRequest) -> PageInfoResponse:
        """等待页面 URL 包含指定关键字。"""
        return browser_service.rpa_wait_url_contains(request)

    def screenshot(self, request: RpaScreenshotRequest) -> RpaScreenshotResponse:
        """页面截图并保存到本地文件。"""
        return browser_service.rpa_screenshot(request)


rpa_page_service = RpaPageService()
