import logging
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.schemas.desktop import ClickImageRequest
from app.services.common.image_normalize import normalize_image_paths, normalize_match_mode
from app.utils.image_utils import click_images_until_found

logger = logging.getLogger(__name__)
settings = get_settings()


def split_image_paths(value: str | None) -> list[str]:
    """将 .env 中以英文分号分隔的图像路径解析为去重后的路径数组。

    示例：
        C:/a.png;C:/b.png -> ['C:/a.png', 'C:/b.png']

    空字符串、空白项会被过滤；重复路径会在 normalize_image_paths 中去重。
    """
    if not value:
        return []
    return normalize_image_paths([item.strip() for item in value.split(';') if item and item.strip()])


@dataclass
class BusinessImageClickOptions:
    """业务图像点击参数。

    说明：
    - click_offset_x/click_offset_y 是相对匹配图片区域左上角的偏移；
    - 两者都为 None 时，底层默认点击匹配框中心点；
    - enabled=False 时不会执行图像查找和点击。
    """

    enabled: bool
    image_paths: list[str] = field(default_factory=list)
    match_mode: str = 'or'
    confidence: float = 0.9
    timeout_ms: int = 10000
    retry_interval_ms: int = 400
    click_offset_x: int | None = None
    click_offset_y: int | None = None


@dataclass
class BusinessImageClickResult:
    clicked: bool
    skipped: bool
    image_paths: list[str]
    match_mode: str
    clicked_images: list[dict] = field(default_factory=list)
    error: str | None = None
    skip_reason: str | None = None
    click_offset_x: int | None = None
    click_offset_y: int | None = None


class BusinessImageClickService:
    """业务公共图像点击服务。

    用于承载“循环查找多张图像 -> 按 or/and 规则点击 -> 返回业务结果”的公共逻辑。
    /biz/page-flow、/biz/page-flow-selenium 或后续其他业务流程都应该复用这一层，
    避免在各个业务接口里重复拼 ClickImageRequest 和重复处理异常。
    """

    def build_auto_click_options(
        self,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> BusinessImageClickOptions:
        """基于当前 .env 配置构造业务图像点击参数。

        这是业务层最常用的入口：接口层只需要传 clickOffsetX/clickOffsetY，
        是否启用、图片路径、匹配模式、相似度、超时、重试间隔都从 .env 读取。
        """
        resolved_click_offset_x, resolved_click_offset_y = self.resolve_click_offset(
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )
        return BusinessImageClickOptions(
            enabled=settings.auto_click_security_check,
            image_paths=split_image_paths(settings.auto_click_image_paths),
            match_mode=normalize_match_mode(settings.auto_click_image_match_mode),
            confidence=settings.auto_click_image_confidence,
            timeout_ms=settings.auto_click_image_timeout_ms,
            retry_interval_ms=settings.auto_click_image_retry_interval_ms,
            click_offset_x=resolved_click_offset_x,
            click_offset_y=resolved_click_offset_y,
        )

    def resolve_click_offset(
        self,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> tuple[int | None, int | None]:
        """解析图像点击偏移。

        优先级：
        1. 接口传入 clickOffsetX/clickOffsetY；
        2. .env 配置 AUTO_CLICK_IMAGE_CLICK_OFFSET_X/Y；
        3. 全部为空时，底层默认点击匹配框中心点。

        注意：clickOffsetX/clickOffsetY 是相对“匹配到的图片区域左上角”的偏移，
        不是相对屏幕左上角。
        """
        has_request_x = click_offset_x is not None
        has_request_y = click_offset_y is not None
        if has_request_x != has_request_y:
            raise ValueError('clickOffsetX/clickOffsetY 需要同时传入，或全部不传')
        if has_request_x and has_request_y:
            return click_offset_x, click_offset_y

        config_x = settings.auto_click_image_click_offset_x
        config_y = settings.auto_click_image_click_offset_y
        has_config_x = config_x is not None
        has_config_y = config_y is not None
        if has_config_x != has_config_y:
            raise ValueError('AUTO_CLICK_IMAGE_CLICK_OFFSET_X/Y 需要同时配置，或全部不配置')
        if has_config_x and has_config_y:
            return config_x, config_y

        return None, None

    def find_and_click_images(
        self,
        options: BusinessImageClickOptions,
        scene: str = 'default',
    ) -> BusinessImageClickResult:
        """公共业务方法：循环查找图像并点击。

        行为保持和原 /biz/page-flow 一致：
        - 未开启或未配置图像路径时返回 clicked=False，不抛错；
        - 找到并点击时返回 clicked=True 和 clickedImages；
        - 超时未找到或点击失败时返回 clicked=False + error，不中断主业务流程。
        """
        image_paths = normalize_image_paths(options.image_paths)
        match_mode = normalize_match_mode(options.match_mode)

        if not options.enabled:
            logger.info(
                '业务图像点击已跳过, scene=%s, enabled=%s, paths=%s',
                scene,
                options.enabled,
                image_paths,
            )
            return BusinessImageClickResult(
                clicked=False,
                skipped=True,
                image_paths=image_paths,
                match_mode=match_mode,
                skip_reason='auto_click_disabled',
                click_offset_x=options.click_offset_x,
                click_offset_y=options.click_offset_y,
            )

        if not image_paths:
            logger.info('业务图像点击已跳过, scene=%s, paths为空', scene)
            return BusinessImageClickResult(
                clicked=False,
                skipped=True,
                image_paths=image_paths,
                match_mode=match_mode,
                skip_reason='image_paths_empty',
                click_offset_x=options.click_offset_x,
                click_offset_y=options.click_offset_y,
            )

        try:
            template_request = self._build_template_request(options, image_paths[0])
            click_results = click_images_until_found(
                image_paths=image_paths,
                confidence=options.confidence,
                timeout_ms=options.timeout_ms,
                retry_interval_ms=options.retry_interval_ms,
                match_mode=match_mode,
                template_request=template_request,
            )
            clicked_images = [result.model_dump() for result in click_results]
            logger.info(
                '业务图像点击成功, scene=%s, matchMode=%s, clickedImages=%s',
                scene,
                match_mode,
                [item.get('imagePath') for item in clicked_images],
            )
            return BusinessImageClickResult(
                clicked=bool(click_results),
                skipped=False,
                image_paths=image_paths,
                match_mode=match_mode,
                clicked_images=clicked_images,
                click_offset_x=options.click_offset_x,
                click_offset_y=options.click_offset_y,
            )
        except Exception as exc:
            logger.warning(
                '业务图像点击失败, scene=%s, paths=%s, matchMode=%s, error=%s',
                scene,
                image_paths,
                match_mode,
                exc,
            )
            return BusinessImageClickResult(
                clicked=False,
                skipped=False,
                image_paths=image_paths,
                match_mode=match_mode,
                error=str(exc),
                click_offset_x=options.click_offset_x,
                click_offset_y=options.click_offset_y,
            )

    @staticmethod
    def _build_template_request(
        options: BusinessImageClickOptions,
        image_path: str,
    ) -> ClickImageRequest:
        """构造用于下层循环查找/点击的请求模板。

        click_images_until_found 会基于该模板替换 imagePath 并保留点击参数，
        因此这里传入第一张图即可，后续多图轮询时会自动替换为当前图。
        """
        return ClickImageRequest(
            imagePath=image_path,
            confidence=options.confidence,
            timeoutMs=options.timeout_ms,
            retryIntervalMs=options.retry_interval_ms,
            clickOffsetX=options.click_offset_x,
            clickOffsetY=options.click_offset_y,
        )


business_image_click_service = BusinessImageClickService()
