from app.schemas.desktop import (
    ClickImageRequest,
    ClickImageResponse,
    ClickPositionRequest,
    ClickPositionResponse,
    OcrClickTextRequest,
    OcrClickTextResponse,
)
from app.visual.screen_manager import screen_manager


class VisualService:
    """给本地业务代码直接调用的图像/屏幕服务层。"""

    def click_position(self, request: ClickPositionRequest) -> ClickPositionResponse:
        return screen_manager.click_position(request)

    def click_image(self, request: ClickImageRequest) -> ClickImageResponse:
        return screen_manager.click_image(request)

    def ocr_click_text_reserved(self, request: OcrClickTextRequest) -> OcrClickTextResponse:
        return screen_manager.ocr_click_text_reserved(request)


visual_service = VisualService()
