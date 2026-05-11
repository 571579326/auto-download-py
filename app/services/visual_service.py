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
from app.schemas.rpa import RpaImageLocateRequest, RpaImageLocateResponse
from app.services.common.image_normalize import normalize_image_paths, normalize_match_mode
from app.runtime.visual.screen_manager import screen_manager


class VisualService:

    def locate_image(self, request: RpaImageLocateRequest) -> RpaImageLocateResponse:
        return screen_manager.locate_image(request)

    def click_position(self, request: ClickPositionRequest) -> ClickPositionResponse:
        return screen_manager.click_position(request)

    def click_image(self, request: ClickImageRequest) -> ClickImageResponse:
        return screen_manager.click_image(request)

    def click_images(self, request: ClickImagesRequest) -> ClickImagesResponse:
        paths = _normalize_image_paths(request)
        mode = normalize_match_mode(request.matchMode)
        clicked = screen_manager.click_images(request=request, image_paths=paths, match_mode=mode)
        return ClickImagesResponse(clicked=bool(clicked), matchMode=mode, clickedImages=clicked)

    def ocr_click_text_reserved(self, request: OcrClickTextRequest) -> OcrClickTextResponse:
        return screen_manager.ocr_click_text_reserved(request)


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


visual_service = VisualService()
