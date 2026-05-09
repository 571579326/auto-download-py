import logging
import time

from app.core.config import get_settings
from app.schemas.browser import BatchOpenPagesResponse
from app.services.browser_service import browser_service
from app.services.business_image_click_service import (
    BusinessImageClickResult,
    business_image_click_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()


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
        - 图像判断走 business_image_click_service 公共业务层，不依赖 Playwright Page。
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
        打开 configCode 对应页面后立刻 driver.quit() 断开，再调用公共业务层执行桌面图像判断。
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
        image_click_options = business_image_click_service.build_auto_click_options(
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )
        page_stabilize_seconds = settings.page_stabilize_seconds

        logger.info(
            'Step1: 准备以%s模式打开配置页面, configCode=%s, clickOffset=(%s,%s)',
            open_mode,
            config_code,
            image_click_options.click_offset_x,
            image_click_options.click_offset_y,
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

            image_click_result = self._find_and_click_images_for_page_flow(
                open_mode=open_mode,
                config_code=config_code,
                options=image_click_options,
            )

            logger.info(
                'Step4: 业务流程执行完成, mode=%s, windowId=%s, imageClicked=%s',
                open_mode,
                window_id,
                image_click_result.clicked,
            )

            return self._build_page_flow_result(
                config_code=config_code,
                open_mode=open_mode,
                pages_response=pages_response,
                image_click_result=image_click_result,
            )
        except Exception:
            logger.exception('业务流程执行异常, mode=%s, configCode=%s', open_mode, config_code)
            raise

    def _find_and_click_images_for_page_flow(
        self,
        open_mode: str,
        config_code: str,
        options,
    ) -> BusinessImageClickResult:
        """page-flow 专用门面：调用公共业务图像点击服务。

        真正的“循环查找图像 -> 命中后点击 -> 失败降级为 imageClicked=False”
        已抽到 business_image_click_service.find_and_click_images，
        这里仅保留 page-flow 的 Step 日志和场景名。
        """
        result = business_image_click_service.find_and_click_images(
            options=options,
            scene=f'page-flow:{open_mode}:{config_code}',
        )
        if result.clicked:
            logger.info(
                'Step3: 图像已找到并点击成功, mode=%s, matchMode=%s, clickedImages=%s',
                open_mode,
                result.match_mode,
                [item.get('imagePath') for item in result.clicked_images],
            )
        elif result.skipped:
            logger.info(
                'Step3: 已跳过自动点击安全验证图像, mode=%s, skipReason=%s, autoClickSecurityCheck=%s, paths=%s',
                open_mode,
                result.skip_reason,
                settings.auto_click_security_check,
                result.image_paths,
            )
        else:
            logger.warning(
                'Step3: 图像未找到或点击失败, 跳过, mode=%s, paths=%s, matchMode=%s, error=%s',
                open_mode,
                result.image_paths,
                result.match_mode,
                result.error,
            )
        return result

    def _build_page_flow_result(
        self,
        config_code: str,
        open_mode: str,
        pages_response: BatchOpenPagesResponse,
        image_click_result: BusinessImageClickResult,
    ) -> dict:
        return {
            'windowId': pages_response.windowId,
            'pagesOpened': pages_response.total,
            'openedPages': [page.model_dump() for page in pages_response.openedPages],
            'imageClicked': image_click_result.clicked,
            'clickedImages': image_click_result.clicked_images,
            'imagePaths': image_click_result.image_paths,
            'imageMatchMode': image_click_result.match_mode,
            'imageClickOffsetX': image_click_result.click_offset_x,
            'imageClickOffsetY': image_click_result.click_offset_y,
            'imageClickOffsetBase': 'matched_image_top_left',
            'imageError': image_click_result.error,
            'imageClickSkipped': image_click_result.skipped,
            'imageClickSkipReason': image_click_result.skip_reason,
            'configCode': config_code,
            'openMode': open_mode,
            'attachMode': 'short',
            'driverDetached': True,
        }


business_service = BusinessService()
