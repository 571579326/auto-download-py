import logging
import time

from app.schemas.desktop import ClickImageRequest, ClickImageResponse
from app.services.visual_service import visual_service

logger = logging.getLogger(__name__)


def normalize_match_mode(match_mode: str | None) -> str:
    value = (match_mode or 'or').strip().lower()
    if value in {'and', 'all', '和'}:
        return 'and'
    if value in {'or', 'any', '或'}:
        return 'or'
    raise ValueError(f'matchMode仅支持 or/any/或 或 and/all/和，当前值: {match_mode}')


def normalize_image_paths(image_paths: list[str] | None = None, image_path: str | None = None) -> list[str]:
    result: list[str] = []
    if image_paths:
        result.extend([item.strip() for item in image_paths if item and item.strip()])
    if image_path and image_path.strip():
        result.append(image_path.strip())
    return list(dict.fromkeys(result))


def click_image_until_found(
    image_path: str,
    confidence: float = 0.9,
    timeout_ms: int = 10000,
    retry_interval_ms: int = 1000,
) -> ClickImageResponse:
    request = ClickImageRequest(
        imagePath=image_path,
        confidence=confidence,
        timeoutMs=timeout_ms,
        retryIntervalMs=retry_interval_ms,
    )
    return visual_service.click_image(request)


def _build_single_image_request(
    image_path: str,
    confidence: float,
    timeout_ms: int,
    retry_interval_ms: int,
    template_request: ClickImageRequest | None = None,
) -> ClickImageRequest:
    if template_request is None:
        return ClickImageRequest(
            imagePath=image_path,
            confidence=confidence,
            timeoutMs=timeout_ms,
            retryIntervalMs=retry_interval_ms,
        )
    return ClickImageRequest(
        imagePath=image_path,
        confidence=confidence,
        regionLeft=template_request.regionLeft,
        regionTop=template_request.regionTop,
        regionWidth=template_request.regionWidth,
        regionHeight=template_request.regionHeight,
        grayscale=template_request.grayscale,
        clicks=template_request.clicks,
        intervalSeconds=template_request.intervalSeconds,
        button=template_request.button,
        timeoutMs=timeout_ms,
        retryIntervalMs=retry_interval_ms,
        moveDurationSeconds=template_request.moveDurationSeconds,
        clickOffsetX=template_request.clickOffsetX,
        clickOffsetY=template_request.clickOffsetY,
    )


def click_images_until_found(
    image_paths: list[str],
    confidence: float = 0.9,
    timeout_ms: int = 10000,
    retry_interval_ms: int = 1000,
    match_mode: str = 'or',
    template_request: ClickImageRequest | None = None,
) -> list[ClickImageResponse]:
    """
    支持多张图像匹配。

    OR 模式（or/any/或）:
        轮询所有图像，任意一张出现即点击该图像并返回。
    AND 模式（and/all/和）:
        依次查找所有图像，全部找到并点击后才返回。

    超时未满足条件则抛出 RuntimeError。
    """
    paths = normalize_image_paths(image_paths)
    if not paths:
        raise ValueError('imagePaths不能为空')

    mode = normalize_match_mode(match_mode)
    retry_interval_ms = max(int(retry_interval_ms), 100)
    timeout_ms = max(int(timeout_ms), retry_interval_ms)

    if mode == 'and':
        clicked: list[ClickImageResponse] = []
        per_timeout = max(retry_interval_ms, timeout_ms // len(paths))
        for image_path in paths:
            request = _build_single_image_request(
                image_path=image_path,
                confidence=confidence,
                timeout_ms=per_timeout,
                retry_interval_ms=retry_interval_ms,
                template_request=template_request,
            )
            clicked.append(visual_service.click_image(request))
        return clicked

    deadline = time.time() + timeout_ms / 1000
    last_error: Exception | None = None
    index = 0

    while time.time() < deadline:
        image_path = paths[index % len(paths)]
        try:
            request = _build_single_image_request(
                image_path=image_path,
                confidence=confidence,
                timeout_ms=retry_interval_ms,
                retry_interval_ms=retry_interval_ms,
                template_request=template_request,
            )
            return [visual_service.click_image(request)]
        except Exception as exc:
            last_error = exc
        index += 1

    raise RuntimeError(
        f'OR模式: {len(paths)}张图像均未在{timeout_ms / 1000:.1f}秒内找到, paths={paths}, lastError={last_error}'
    )


def click_image_if_exists(
    image_path: str | None,
    confidence: float = 0.9,
    timeout_ms: int = 5000,
    retry_interval_ms: int = 400,
    clicks: int = 1,
    button: str = 'left',
    error_handler=None,
) -> bool:
    """兼容旧版单图点击工具：找到并点击返回 True，未找到或异常返回 False。"""
    if not image_path:
        return False
    try:
        request = ClickImageRequest(
            imagePath=image_path,
            confidence=confidence,
            timeoutMs=timeout_ms,
            retryIntervalMs=retry_interval_ms,
            clicks=clicks,
            button=button,
        )
        visual_service.click_image(request)
        return True
    except Exception as exc:
        if error_handler is not None:
            try:
                error_handler(exc)
            except Exception:
                logger.warning('click_image_if_exists error_handler执行失败', exc_info=True)
        return False
