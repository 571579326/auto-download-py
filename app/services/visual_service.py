from app.schemas.desktop import (
    ClickImageRequest,
    ClickImageResponse,
    ClickImagesRequest,
    ClickImagesResponse,
    ClickPositionRequest,
    ClickPositionResponse,
    OcrClickTextRequest,
    OcrClickTextResponse,
)
from app.visual.screen_manager import screen_manager


def _normalize_match_mode(match_mode: str | None) -> str:
    value = (match_mode or 'or').strip().lower()
    if value in {'and', 'all', '和'}:
        return 'and'
    if value in {'or', 'any', '或'}:
        return 'or'
    raise ValueError(f'matchMode仅支持 or/any/或 或 and/all/和，当前值: {match_mode}')


def _normalize_image_paths(request: ClickImagesRequest) -> list[str]:
    paths: list[str] = []
    if request.imagePaths:
        paths.extend([item.strip() for item in request.imagePaths if item and item.strip()])
    if request.imagePath and request.imagePath.strip():
        paths.append(request.imagePath.strip())
    paths = list(dict.fromkeys(paths))
    if not paths:
        raise ValueError('imagePaths不能为空')
    return paths


class VisualService:
    """给本地业务代码直接调用的图像/屏幕服务层。"""

    def click_position(self, request: ClickPositionRequest) -> ClickPositionResponse:
        return screen_manager.click_position(request)

    def click_image(self, request: ClickImageRequest) -> ClickImageResponse:
        return screen_manager.click_image(request)

    def click_images(self, request: ClickImagesRequest) -> ClickImagesResponse:
        paths = _normalize_image_paths(request)
        mode = _normalize_match_mode(request.matchMode)
        clicked = screen_manager.click_images(request=request, image_paths=paths, match_mode=mode)
        return ClickImagesResponse(clicked=bool(clicked), matchMode=mode, clickedImages=clicked)

    def ocr_click_text_reserved(self, request: OcrClickTextRequest) -> OcrClickTextResponse:
        return screen_manager.ocr_click_text_reserved(request)


visual_service = VisualService()
