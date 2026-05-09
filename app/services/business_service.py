import logging

from app.services.business_common_service import BusinessOpenMode, business_common_service

logger = logging.getLogger(__name__)


class BusinessService:
    """业务接口服务层。

    该类保留对外业务入口方法，具体的公共流程能力下沉到
    business_common_service，方便后续新增业务接口时复用。
    """

    def open_pages_and_check_image(
        self,
        config_code: str,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> dict:
        """原 /biz/page-flow：Playwright 短接管版本。

        流程：打开配置页 -> 等待页面稳定 -> 循环查找配置图像并点击 -> 返回统一结果。
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
        """/biz/page-flow-selenium：Selenium 短接管版本。

        通过 Selenium debuggerAddress 短暂附加到已运行的 Chrome/chromeTest，
        打开配置页面后立即断开，再走同一套公共图像点击流程。
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
        open_mode: BusinessOpenMode,
        click_offset_x: int | None = None,
        click_offset_y: int | None = None,
    ) -> dict:
        """公共业务编排入口。

        这里故意只保留流程编排，不再直接写“打开页面/等待/识图/拼返回”的细节，
        这样后续业务接口可以直接复用 business_common_service 的公共方法。
        """
        context = business_common_service.build_page_flow_context(
            config_code=config_code,
            open_mode=open_mode,
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
        )

        try:
            pages_response = business_common_service.open_config_pages_by_mode(context)
            business_common_service.wait_page_stable(page_count=pages_response.total)
            image_click_result = business_common_service.find_and_click_images_for_flow(context)

            logger.info(
                'Step4: 业务流程执行完成, mode=%s, windowId=%s, imageClicked=%s',
                open_mode,
                pages_response.windowId,
                image_click_result.clicked,
            )
            return business_common_service.build_page_flow_result(
                context=context,
                pages_response=pages_response,
                image_click_result=image_click_result,
            )
        except Exception:
            logger.exception('业务流程执行异常, mode=%s, configCode=%s', open_mode, config_code)
            raise


business_service = BusinessService()
