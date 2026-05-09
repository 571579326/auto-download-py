from typing import Literal

from pydantic import BaseModel, Field


class RpaPageTarget(BaseModel):
    """RPA 页面定位参数。

    windowId 必传；pageId 和 urlContains 二选一或都不传：
    - pageId：精确定位项目内记录的页面；
    - urlContains：按 URL 关键字定位页面；
    - 都不传：优先使用当前活动页，找不到时接管浏览器中最新可用页面。
    """

    windowId: str = Field(description='浏览器窗口ID，来自 /browser/session/open 或 /biz/page-flow 返回值')
    pageId: str | None = Field(default=None, description='可选。页面ID')
    urlContains: str | None = Field(default=None, description='可选。URL 包含的关键字')


class RpaOpenUrlRequest(RpaPageTarget):
    """打开 URL 的 RPA 请求。"""

    url: str = Field(description='要打开的 URL')
    newTab: bool = Field(default=False, description='是否新开标签页')
    bringToFront: bool = Field(default=True, description='打开后是否切到前台')


class RpaOpenTabRequest(RpaPageTarget):
    """打开新标签页请求。"""

    url: str = Field(default='about:blank', description='新标签页 URL')
    bringToFront: bool = Field(default=True, description='是否切到前台')


class RpaPageWaitLoadStateRequest(RpaPageTarget):
    """等待页面加载状态请求。"""

    state: Literal['load', 'domcontentloaded', 'networkidle'] = Field(default='domcontentloaded')
    timeoutMs: int = Field(default=10000, ge=100, description='超时时间，毫秒')


class RpaPageReloadRequest(RpaPageTarget):
    """刷新页面请求。"""

    waitUntil: Literal['load', 'domcontentloaded', 'networkidle'] = Field(default='domcontentloaded')
    timeoutMs: int = Field(default=10000, ge=100, description='超时时间，毫秒')


class RpaPageWaitUrlRequest(RpaPageTarget):
    """等待 URL 包含指定关键字请求。"""

    urlContainsTarget: str = Field(description='等待 URL 中出现的关键字')
    timeoutMs: int = Field(default=10000, ge=100)
    retryIntervalMs: int = Field(default=300, ge=50)


class RpaScreenshotRequest(RpaPageTarget):
    """页面截图请求。"""

    path: str | None = Field(default=None, description='可选。截图保存路径，不传则保存到 screenshots 目录')
    fullPage: bool = Field(default=True, description='是否截取完整页面')


class RpaScreenshotResponse(BaseModel):
    """页面截图响应。"""

    success: bool
    path: str
    windowId: str
    pageId: str | None = None
    title: str | None = None
    url: str | None = None
