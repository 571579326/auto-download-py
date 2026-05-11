import logging
import os
import time

from app.core.config import get_settings
from app.schemas.desktop import (
    ActivateWindowRequest,
    ClickImageRequest,
    ClickImageResponse,
    ClickImagesRequest,
    ClickPositionRequest,
    ClickPositionResponse,
    OcrClickTextRequest,
    OcrClickTextResponse,
)
from app.schemas.rpa import RpaImageLocateRequest, RpaImageLocateResponse


logger = logging.getLogger(__name__)
settings = get_settings()
_DPI_AWARENESS_SET = False


def _require_windows() -> None:
    if os.name != 'nt':
        raise RuntimeError('图像/屏幕自动化当前仅支持 Windows')


def _ensure_dpi_awareness() -> None:
    """尽量让 pyautogui 截图坐标和 Windows 物理坐标一致。"""
    global _DPI_AWARENESS_SET
    if _DPI_AWARENESS_SET or os.name != 'nt':
        return
    try:
        import ctypes

        try:
            # Windows 8.1+
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            # Windows 7/8 fallback
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        logger.debug('设置 DPI awareness 失败，继续使用当前进程 DPI 设置', exc_info=True)
    finally:
        _DPI_AWARENESS_SET = True


def _activate_window_before_click() -> None:
    if not settings.auto_click_activate_window_before:
        return
    title_regex = (settings.auto_click_window_title_regex or '').strip()
    if not title_regex:
        return
    try:
        from app.runtime.desktop.windows_manager import windows_manager

        windows_manager.activate_window(
            ActivateWindowRequest(
                backend='uia',
                titleRegex=title_regex,
                timeoutMs=2000,
                restoreIfMinimized=True,
            )
        )
        time.sleep(0.1)
    except Exception as exc:
        logger.warning('点击前激活窗口失败，继续尝试点击, titleRegex=%s, error=%s', title_regex, exc)


class ScreenManager:
    def _pyautogui(self):
        _require_windows()
        _ensure_dpi_awareness()
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError('未安装 pyautogui，请先执行 uv sync 或安装 requirements.txt') from exc
        pyautogui.FAILSAFE = True
        return pyautogui

    @staticmethod
    def _build_region(request: ClickImageRequest):
        fields = [request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight]
        if all(value is None for value in fields):
            return None
        if any(value is None for value in fields):
            raise ValueError('regionLeft/regionTop/regionWidth/regionHeight 需要同时传入，或全部不传')
        return (request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight)

    @staticmethod
    def _build_click_point(pyautogui, box, request: ClickImageRequest):
        """
        构造实际点击坐标。

        clickOffsetX/clickOffsetY 的含义：
        - 两者都不传：点击匹配框中心点；
        - 两者都传：点击 匹配框左上角 + 偏移量；
        - 只传一个：报错，避免误点。
        """
        center = pyautogui.center(box)
        has_offset_x = request.clickOffsetX is not None
        has_offset_y = request.clickOffsetY is not None
        if has_offset_x != has_offset_y:
            raise ValueError('clickOffsetX/clickOffsetY 需要同时传入，或全部不传')
        if has_offset_x and has_offset_y:
            return int(box.left + request.clickOffsetX), int(box.top + request.clickOffsetY), center
        return int(center.x), int(center.y), center


    @staticmethod
    def _build_locate_region(request: RpaImageLocateRequest):
        """构造图像查找区域；四个区域字段必须同时为空或同时有值。"""
        fields = [request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight]
        if all(value is None for value in fields):
            return None
        if any(value is None for value in fields):
            raise ValueError('regionLeft/regionTop/regionWidth/regionHeight 需要同时传入，或全部不传')
        return (request.regionLeft, request.regionTop, request.regionWidth, request.regionHeight)

    def locate_image(self, request: RpaImageLocateRequest) -> RpaImageLocateResponse:
        """只查找图像，不点击。

        该方法用于等待、断言、调试坐标等 RPA 场景。坐标以屏幕左上角为原点。
        """
        if not request.imagePath:
            raise ValueError('imagePath不能为空')
        if not os.path.exists(request.imagePath):
            raise ValueError(f'imagePath不存在: {request.imagePath}')

        pyautogui = self._pyautogui()
        region = self._build_locate_region(request)
        deadline = time.time() + request.timeoutMs / 1000
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                box = pyautogui.locateOnScreen(
                    request.imagePath,
                    confidence=request.confidence,
                    region=region,
                    grayscale=request.grayscale,
                )
                if box is not None:
                    center = pyautogui.center(box)
                    return RpaImageLocateResponse(
                        found=True,
                        imagePath=request.imagePath,
                        confidence=request.confidence,
                        centerX=int(center.x),
                        centerY=int(center.y),
                        left=int(box.left),
                        top=int(box.top),
                        width=int(box.width),
                        height=int(box.height),
                    )
            except Exception as exc:
                last_error = exc
            time.sleep(request.retryIntervalMs / 1000)

        return RpaImageLocateResponse(
            found=False,
            imagePath=request.imagePath,
            confidence=request.confidence,
            error=str(last_error) if last_error else 'timeout',
        )

    def click_position(self, request: ClickPositionRequest) -> ClickPositionResponse:
        pyautogui = self._pyautogui()
        pyautogui.click(
            x=request.x,
            y=request.y,
            clicks=request.clicks,
            interval=request.intervalSeconds,
            button=request.button,
            duration=request.durationSeconds,
        )
        return ClickPositionResponse(
            clicked=True,
            x=request.x,
            y=request.y,
            clicks=request.clicks,
            button=request.button,
        )

    def click_image(self, request: ClickImageRequest) -> ClickImageResponse:
        if not request.imagePath:
            raise ValueError('imagePath不能为空')
        if not os.path.exists(request.imagePath):
            raise ValueError(f'imagePath不存在: {request.imagePath}')

        pyautogui = self._pyautogui()
        region = self._build_region(request)
        deadline = time.time() + request.timeoutMs / 1000
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                box = pyautogui.locateOnScreen(
                    request.imagePath,
                    confidence=request.confidence,
                    region=region,
                    grayscale=request.grayscale,
                )
                if box is not None:
                    click_x, click_y, center = self._build_click_point(pyautogui, box, request)
                    logger.info(
                        '图像命中，准备点击, imagePath=%s, box=(left=%s, top=%s, width=%s, height=%s), center=(%s,%s), click=(%s,%s), offset=(%s,%s)',
                        request.imagePath,
                        int(box.left),
                        int(box.top),
                        int(box.width),
                        int(box.height),
                        int(center.x),
                        int(center.y),
                        click_x,
                        click_y,
                        request.clickOffsetX,
                        request.clickOffsetY,
                    )
                    _activate_window_before_click()
                    pyautogui.click(
                        x=click_x,
                        y=click_y,
                        clicks=request.clicks,
                        interval=request.intervalSeconds,
                        button=request.button,
                        duration=request.moveDurationSeconds,
                    )
                    return ClickImageResponse(
                        clicked=True,
                        centerX=int(center.x),
                        centerY=int(center.y),
                        left=int(box.left),
                        top=int(box.top),
                        width=int(box.width),
                        height=int(box.height),
                        imagePath=request.imagePath,
                        confidence=request.confidence,
                        clickX=click_x,
                        clickY=click_y,
                    )
            except Exception as exc:
                last_error = exc
            time.sleep(request.retryIntervalMs / 1000)

        if last_error is not None:
            raise RuntimeError(f'按图片点击失败: {last_error}') from last_error
        raise RuntimeError(
            f'超时未找到目标图片: imagePath={request.imagePath}, confidence={request.confidence}, region={region}'
        )

    def click_images(
        self,
        request: ClickImagesRequest,
        image_paths: list[str],
        match_mode: str,
    ) -> list[ClickImageResponse]:
        if not image_paths:
            raise ValueError('imagePaths不能为空')

        retry_interval_ms = max(int(request.retryIntervalMs), 100)
        timeout_ms = max(int(request.timeoutMs), retry_interval_ms)

        def build_request(path: str, timeout: int) -> ClickImageRequest:
            return ClickImageRequest(
                imagePath=path,
                confidence=request.confidence,
                regionLeft=request.regionLeft,
                regionTop=request.regionTop,
                regionWidth=request.regionWidth,
                regionHeight=request.regionHeight,
                grayscale=request.grayscale,
                clicks=request.clicks,
                intervalSeconds=request.intervalSeconds,
                button=request.button,
                timeoutMs=timeout,
                retryIntervalMs=retry_interval_ms,
                moveDurationSeconds=request.moveDurationSeconds,
                clickOffsetX=request.clickOffsetX,
                clickOffsetY=request.clickOffsetY,
            )

        if match_mode == 'and':
            clicked: list[ClickImageResponse] = []
            per_timeout = max(retry_interval_ms, timeout_ms // len(image_paths))
            for image_path in image_paths:
                clicked.append(self.click_image(build_request(image_path, per_timeout)))
            return clicked

        deadline = time.time() + timeout_ms / 1000
        last_error: Exception | None = None
        index = 0
        while time.time() < deadline:
            image_path = image_paths[index % len(image_paths)]
            try:
                return [self.click_image(build_request(image_path, retry_interval_ms))]
            except Exception as exc:
                last_error = exc
            index += 1

        raise RuntimeError(
            f'OR模式: {len(image_paths)}张图像均未在{timeout_ms / 1000:.1f}秒内找到, paths={image_paths}, lastError={last_error}'
        )

    def ocr_click_text_reserved(self, request: OcrClickTextRequest) -> OcrClickTextResponse:
        message = (
            '已预留 OCR 点击接口，当前未默认实现。后续可接入 cnOCR：'
            '先截图，再识别文本框位置，再结合 PyAutoGUI/Windows 层完成点击。'
            f' 当前参数: text={request.text}, contains={request.contains}, confidence={request.confidence}'
        )
        return OcrClickTextResponse(reserved=True, message=message)


screen_manager = ScreenManager()
