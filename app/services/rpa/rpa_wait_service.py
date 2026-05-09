import time

from app.schemas.rpa import (
    RpaElementTextRequest,
    RpaImageLocateRequest,
    RpaPageWaitLoadStateRequest,
    RpaPageWaitUrlRequest,
    RpaWaitSleepRequest,
)
from app.services.rpa.rpa_element_service import rpa_element_service
from app.services.rpa.rpa_image_service import rpa_image_service
from app.services.rpa.rpa_page_service import rpa_page_service


class RpaWaitService:
    """RPA 等待公共方法层。

    不同于业务里的固定 sleep，这里按动作分类封装等待：页面加载、URL变化、元素出现、图像出现。
    """

    def sleep(self, request: RpaWaitSleepRequest) -> dict:
        """固定等待指定秒数。"""
        time.sleep(request.seconds)
        return {'success': True, 'seconds': request.seconds}

    def page_load_state(self, request: RpaPageWaitLoadStateRequest):
        """等待页面加载状态。"""
        return rpa_page_service.wait_load_state(request)

    def url_contains(self, request: RpaPageWaitUrlRequest):
        """等待 URL 包含指定关键字。"""
        return rpa_page_service.wait_url_contains(request)

    def element_exists(self, request: RpaElementTextRequest):
        """等待 DOM 元素出现。"""
        result = rpa_element_service.exists(request)
        if not result.exists:
            raise RuntimeError(f'等待元素出现超时: {request.selector}')
        return result

    def image_exists(self, request: RpaImageLocateRequest):
        """等待图像出现。"""
        return rpa_image_service.wait(request)


rpa_wait_service = RpaWaitService()
