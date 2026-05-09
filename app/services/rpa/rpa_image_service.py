from app.schemas.desktop import ClickImageRequest, ClickImagesRequest
from app.schemas.rpa import (
    RpaImageClickManyRequest,
    RpaImageClickRequest,
    RpaImageLocateRequest,
    RpaImageLocateResponse,
)
from app.services.visual_service import visual_service


class RpaImageService:
    """RPA 图像公共方法层。

    用于没有稳定 DOM selector、或要处理浏览器外弹窗/验证框/客户端界面时的屏幕图像能力。
    所有坐标均以屏幕左上角为原点；点击偏移以匹配到的图片左上角为原点。
    """

    def locate(self, request: RpaImageLocateRequest) -> RpaImageLocateResponse:
        """查找图像但不点击，适合调试坐标、等待、断言。"""
        return visual_service.locate_image(request)

    def wait(self, request: RpaImageLocateRequest) -> RpaImageLocateResponse:
        """等待图像出现；本质是带超时的 locate。"""
        result = visual_service.locate_image(request)
        if not result.found:
            raise RuntimeError(f'等待图像出现超时: {request.imagePath}, error={result.error}')
        return result

    def click(self, request: RpaImageClickRequest):
        """查找并点击单张图像。"""
        return visual_service.click_image(
            ClickImageRequest(
                imagePath=request.imagePath,
                confidence=request.confidence,
                regionLeft=request.regionLeft,
                regionTop=request.regionTop,
                regionWidth=request.regionWidth,
                regionHeight=request.regionHeight,
                grayscale=request.grayscale,
                clicks=request.clicks,
                intervalSeconds=request.intervalSeconds,
                button=request.button,
                timeoutMs=request.timeoutMs,
                retryIntervalMs=request.retryIntervalMs,
                moveDurationSeconds=request.moveDurationSeconds,
                clickOffsetX=request.clickOffsetX,
                clickOffsetY=request.clickOffsetY,
            )
        )

    def click_many(self, request: RpaImageClickManyRequest):
        """按 OR/AND 模式查找并点击多张图像。"""
        return visual_service.click_images(
            ClickImagesRequest(
                imagePaths=request.imagePaths,
                imagePath=request.imagePath,
                matchMode=request.matchMode,
                confidence=request.confidence,
                regionLeft=request.regionLeft,
                regionTop=request.regionTop,
                regionWidth=request.regionWidth,
                regionHeight=request.regionHeight,
                grayscale=request.grayscale,
                clicks=request.clicks,
                intervalSeconds=request.intervalSeconds,
                button=request.button,
                timeoutMs=request.timeoutMs,
                retryIntervalMs=request.retryIntervalMs,
                moveDurationSeconds=request.moveDurationSeconds,
                clickOffsetX=request.clickOffsetX,
                clickOffsetY=request.clickOffsetY,
            )
        )


rpa_image_service = RpaImageService()
