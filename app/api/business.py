from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import Result
from app.services.business_service import business_service

router = APIRouter(prefix='/biz', tags=['business'])


@router.post('/page-flow')
async def execute_page_flow(
    configCode: Annotated[str, Query(description='ad_browser_page_config 表的 config_code')],
    clickOffsetX: Annotated[int | None, Query(description='点击偏移X：相对匹配图片区域左上角，需和clickOffsetY同时传入')] = None,
    clickOffsetY: Annotated[int | None, Query(description='点击偏移Y：相对匹配图片区域左上角，需和clickOffsetX同时传入')] = None,
):
    """
    执行业务流程（Playwright 短接管版）：

    1. 如 Chrome 调试端口未启动，先用纯净模式启动浏览器；
    2. Playwright 仅短暂 connect_over_cdp，打开 configCode 配置页面后立即断开；
    3. 等待页面稳定后，按内部配置查找图像并点击，超时则跳过。
    """
    data = await run_in_threadpool(
        business_service.open_pages_and_check_image,
        configCode,
        clickOffsetX,
        clickOffsetY,
    )
    return Result(message='pageFlow 执行成功', data=data)


@router.post('/page-flow-selenium')
async def execute_page_flow_selenium(
    configCode: Annotated[str, Query(description='ad_browser_page_config 表的 config_code')],
    clickOffsetX: Annotated[int | None, Query(description='点击偏移X：相对匹配图片区域左上角，需和clickOffsetY同时传入')] = None,
    clickOffsetY: Annotated[int | None, Query(description='点击偏移Y：相对匹配图片区域左上角，需和clickOffsetX同时传入')] = None,
):
    """
    执行业务流程（Selenium 短接管复现版）：

    1. 如 Chrome 调试端口未启动，先用纯净模式启动浏览器；
    2. Selenium 通过 debuggerAddress 短暂附加，打开 configCode 配置页面后 driver.quit() 断开；
    3. 等待页面稳定后，按内部配置查找图像并点击，超时则跳过。
    """
    data = await run_in_threadpool(
        business_service.open_pages_and_check_image_selenium,
        configCode,
        clickOffsetX,
        clickOffsetY,
    )
    return Result(message='pageFlowSelenium 执行成功', data=data)
