import logging
import time
from dataclasses import dataclass
from typing import Literal

from app.core.config import get_settings
from app.schemas.browser import BatchOpenPagesResponse
from app.services.browser_service import browser_service
from app.services.business_image_click_service import (
    BusinessImageClickOptions,
    BusinessImageClickResult,
    business_image_click_service,
)

logger = logging.getLogger(__name__)
settings = get_settings()

BusinessOpenMode = Literal['playwright_once', 'selenium_once']


@dataclass(frozen=True)
class BusinessPageFlowContext:
    """业务页面流程上下文。

    这个对象只保存一次业务流程中会重复使用的关键参数，避免各个业务方法之间
    反复传 config_code/open_mode/click_offset 等散乱参数。
    """

    config_code: str
    open_mode: BusinessOpenMode
    image_click_options: BusinessImageClickOptions

    @property
    def scene(self) -> str:
        """返回图像点击日志使用的场景名。"""
        return f'page-flow:{self.open_mode}:{self.config_code}'


class BusinessCommonService:
    """业务层公共方法。

    该类只放“可被多个业务接口复用”的流程级公共能力，例如：
    - 根据接口参数和 .env 生成图像点击参数；
    - 按指定短接管模式打开配置页面；
    - 等待页面稳定；
    - 执行业务图像点击并统一记录日志；
    - 组装 page-flow 风格的统一返回结构。

    后续如果新增 /biz/xxx 接口，优先复用这里的方法，避免把浏览器打开、页面稳定、
    图像点击、异常降级这些流程复制到新的 service 里。
    """

    def build_page_flow_context(
        self,
        config_code: str,
        open_mode: BusinessOpenMode,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> BusinessPageFlowContext:
        """创建业务流程上下文。

        click_offset_x/click_offset_y 的解析规则统一委托给
        business_image_click_service.build_auto_click_options：
        1. 接口参数优先；
        2. 接口参数为空时读取 .env；
        3. 都为空时底层默认点击匹配框中心点。
        """
        self.validate_open_mode(open_mode)
        image_click_options = business_image_click_service.build_auto_click_options(
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )
        return BusinessPageFlowContext(
            config_code=config_code,
            open_mode=open_mode,
            image_click_options=image_click_options,
        )

    @staticmethod
    def validate_open_mode(open_mode: str) -> None:
        """校验业务页面打开模式。"""
        if open_mode not in {'playwright_once', 'selenium_once'}:
            raise ValueError(f'不支持的业务打开模式: {open_mode}')

    def open_config_pages_by_mode(self, context: BusinessPageFlowContext) -> BatchOpenPagesResponse:
        """按上下文指定的短接管模式打开配置页面。

        playwright_once：Playwright connect_over_cdp 短暂接管，打开页面后立即断开。
        selenium_once：Selenium debuggerAddress 短暂附加，打开页面后立即 driver.quit()。
        """
        logger.info(
            'Step1: 准备以%s模式打开配置页面, configCode=%s, clickOffset=(%s,%s)',
            context.open_mode,
            context.config_code,
            context.image_click_options.click_offset_x,
            context.image_click_options.click_offset_y,
        )

        if context.open_mode == 'selenium_once':
            pages_response = browser_service.open_config_pages_selenium_once(config_code=context.config_code)
        else:
            pages_response = browser_service.open_config_pages_playwright_once(config_code=context.config_code)

        logger.info(
            'Step2: 配置页面已打开, mode=%s, configCode=%s, windowId=%s, total=%s',
            context.open_mode,
            context.config_code,
            pages_response.windowId,
            pages_response.total,
        )
        return pages_response

    @staticmethod
    def wait_page_stable(page_count: int, seconds: float | None = None) -> None:
        """等待页面稳定。

        只有实际打开了页面且等待时间大于 0 时才 sleep，避免空配置或显式关闭等待时浪费时间。
        """
        wait_seconds = settings.page_stabilize_seconds if seconds is None else seconds
        if wait_seconds > 0 and page_count > 0:
            logger.info('Step2.1: 等待页面稳定, seconds=%s, pageCount=%s', wait_seconds, page_count)
            time.sleep(wait_seconds)

    def find_and_click_images_for_flow(self, context: BusinessPageFlowContext) -> BusinessImageClickResult:
        """执行业务图像点击。

        该方法统一封装 page-flow 场景下的日志输出；真正的循环识图、点击、异常降级
        仍由 business_image_click_service.find_and_click_images 负责。
        """
        result = business_image_click_service.find_and_click_images(
            options=context.image_click_options,
            scene=context.scene,
        )
        if result.clicked:
            logger.info(
                'Step3: 图像已找到并点击成功, mode=%s, matchMode=%s, clickedImages=%s',
                context.open_mode,
                result.match_mode,
                [item.get('imagePath') for item in result.clicked_images],
            )
        elif result.skipped:
            logger.info(
                'Step3: 已跳过自动点击安全验证图像, mode=%s, skipReason=%s, autoClickSecurityCheck=%s, paths=%s',
                context.open_mode,
                result.skip_reason,
                settings.auto_click_security_check,
                result.image_paths,
            )
        else:
            logger.warning(
                'Step3: 图像未找到或点击失败, 跳过, mode=%s, paths=%s, matchMode=%s, error=%s',
                context.open_mode,
                result.image_paths,
                result.match_mode,
                result.error,
            )
        return result

    @staticmethod
    def build_page_flow_result(
        context: BusinessPageFlowContext,
        pages_response: BatchOpenPagesResponse,
        image_click_result: BusinessImageClickResult,
    ) -> dict:
        """组装 /biz/page-flow 与 /biz/page-flow-selenium 的统一返回体。"""
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
            'configCode': context.config_code,
            'openMode': context.open_mode,
            'attachMode': 'short',
            'driverDetached': True,
        }


business_common_service = BusinessCommonService()
