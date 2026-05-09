import logging
import time

from app.core.config import get_settings
from app.schemas.browser import BatchOpenPagesResponse
from app.schemas.desktop import ClickImageRequest
from app.services.browser_service import browser_service
from app.utils.image_utils import click_images_until_found

logger = logging.getLogger(__name__)
settings = get_settings()


def _split_auto_click_image_paths(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(';') if item and item.strip()]


class BusinessService:
    def open_pages_and_check_image(
        self,
        config_code: str,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> dict:
        """原 /biz/page-flow：Playwright 短接管版本。

        与旧版不同：
        - 不调用 browser_service.open_browser() 创建长期 Playwright runtime；
        - 不走 browser_service.open_config_pages() 的长期窗口上下文；
        - 只在打开配置页的一瞬间 connect_over_cdp，发起跳转后立即断开；
        - 图像判断仍走桌面截图，不依赖 Playwright Page。
        """
        return self._open_pages_and_check_image_by_mode(
            config_code=config_code,
            open_mode='playwright_once',
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )

    def open_pages_and_check_image_selenium(
        self,
        config_code: str,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> dict:
        """Selenium 复现版本。

        通过 Selenium debuggerAddress 短暂附加到已运行的 Chrome/chromeTest，
        打开 configCode 对应页面后立刻 driver.quit() 断开，再执行桌面图像判断。
        """
        return self._open_pages_and_check_image_by_mode(
            config_code=config_code,
            open_mode='selenium_once',
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )

    def _open_pages_and_check_image_by_mode(
        self,
        config_code: str,
        open_mode: str,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> dict:
        image_paths = _split_auto_click_image_paths(settings.auto_click_image_paths)
        image_confidence = settings.auto_click_image_confidence
        image_timeout_ms = settings.auto_click_image_timeout_ms
        image_retry_interval_ms = settings.auto_click_image_retry_interval_ms
        page_stabilize_seconds = settings.page_stabilize_seconds
        match_mode = settings.auto_click_image_match_mode
        resolved_click_offset_x, resolved_click_offset_y = self._resolve_click_offset(
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )

        logger.info(
            'Step1: 准备以%s模式打开配置页面, configCode=%s, clickOffset=(%s,%s)',
            open_mode,
            config_code,
            resolved_click_offset_x,
            resolved_click_offset_y,
        )

        try:
            if open_mode == 'selenium_once':
                pages_response = browser_service.open_config_pages_selenium_once(config_code=config_code)
            elif open_mode == 'playwright_once':
                pages_response = browser_service.open_config_pages_playwright_once(config_code=config_code)
            else:
                raise ValueError(f'不支持的业务打开模式: {open_mode}')

            window_id = pages_response.windowId
            page_count = pages_response.total
            logger.info(
                'Step2: 配置页面已打开, mode=%s, configCode=%s, windowId=%s, total=%s',
                open_mode,
                config_code,
                window_id,
                page_count,
            )

            if page_stabilize_seconds > 0 and page_count > 0:
                time.sleep(page_stabilize_seconds)

            image_clicked = False
            clicked_images: list[dict] = []
            image_error: str | None = None
            if image_paths and settings.auto_click_security_check:
                try:
                    template_request = ClickImageRequest(
                        imagePath=image_paths[0],
                        confidence=image_confidence,
                        timeoutMs=image_timeout_ms,
                        retryIntervalMs=image_retry_interval_ms,
                        clickOffsetX=resolved_click_offset_x,
                        clickOffsetY=resolved_click_offset_y,
                    )
                    click_results = click_images_until_found(
                        image_paths=image_paths,
                        confidence=image_confidence,
                        timeout_ms=image_timeout_ms,
                        retry_interval_ms=image_retry_interval_ms,
                        match_mode=match_mode,
                        template_request=template_request,
                    )
                    image_clicked = bool(click_results)
                    clicked_images = [result.model_dump() for result in click_results]
                    logger.info(
                        'Step3: 图像已找到并点击成功, mode=%s, matchMode=%s, clickedImages=%s',
                        open_mode,
                        match_mode,
                        [item.get('imagePath') for item in clicked_images],
                    )
                except Exception as e:
                    image_error = str(e)
                    logger.warning(
                        'Step3: 图像未找到或点击失败, 跳过, mode=%s, paths=%s, matchMode=%s, error=%s',
                        open_mode,
                        image_paths,
                        match_mode,
                        e,
                    )
            else:
                logger.info(
                    'Step3: 已跳过自动点击安全验证图像, mode=%s, autoClickSecurityCheck=%s, paths=%s',
                    open_mode,
                    settings.auto_click_security_check,
                    image_paths,
                )

            logger.info(
                'Step4: 业务流程执行完成, mode=%s, windowId=%s, imageClicked=%s',
                open_mode,
                window_id,
                image_clicked,
            )

            return self._build_page_flow_result(
                config_code=config_code,
                open_mode=open_mode,
                pages_response=pages_response,
                image_clicked=image_clicked,
                clicked_images=clicked_images,
                image_paths=image_paths,
                match_mode=match_mode,
                image_error=image_error,
                click_offset_x=resolved_click_offset_x,
                click_offset_y=resolved_click_offset_y,
            )
        except Exception:
            logger.exception('业务流程执行异常, mode=%s, configCode=%s', open_mode, config_code)
            raise

    def _resolve_click_offset(
        self,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> tuple[int | None, int | None]:
        """
        解析图像点击偏移。

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

    def _build_page_flow_result(
        self,
        config_code: str,
        open_mode: str,
        pages_response: BatchOpenPagesResponse,
        image_clicked: bool,
        clicked_images: list[dict],
        image_paths: list[str],
        match_mode: str,
        image_error: str | None,
        click_offset_x: int | None,
        click_offset_y: int | None,
    ) -> dict:
        return {
            'windowId': pages_response.windowId,
            'pagesOpened': pages_response.total,
            'openedPages': [page.model_dump() for page in pages_response.openedPages],
            'imageClicked': image_clicked,
            'clickedImages': clicked_images,
            'imagePaths': image_paths,
            'imageMatchMode': match_mode,
            'imageClickOffsetX': click_offset_x,
            'imageClickOffsetY': click_offset_y,
            'imageClickOffsetBase': 'matched_image_top_left',
            'imageError': image_error,
            'configCode': config_code,
            'openMode': open_mode,
            'attachMode': 'short',
            'driverDetached': True,
        }


business_service = BusinessService()
