from typing import Literal

from pydantic import BaseModel, Field


# ============================ page ============================
class RpaPageTarget(BaseModel):
    """RPA 页面定位参数。"""

    windowId: str = Field(description='浏览器窗口ID')
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

    path: str | None = Field(default=None, description='可选。截图保存路径')
    fullPage: bool = Field(default=True, description='是否截取完整页面')


class RpaScreenshotResponse(BaseModel):
    """页面截图响应。"""

    success: bool
    path: str
    windowId: str
    pageId: str | None = None
    title: str | None = None
    url: str | None = None


# ============================ element ============================
class RpaElementBaseRequest(RpaPageTarget):
    """元素操作基础请求。"""

    selector: str | None = Field(default=None, description='CSS/XPath 选择器')
    text: str | None = Field(default=None, description='元素可见文本')
    attr: str | None = Field(default=None, description='元素属性值')
    role: str | None = Field(default=None, description='ARIA role')
    exact: bool = Field(default=False, description='是否精确匹配')
    timeoutMs: int = Field(default=5000, ge=100, description='超时时间，毫秒')


class RpaElementClickRequest(RpaElementBaseRequest):
    """元素点击请求。"""

    clickCount: int = Field(default=1, ge=1, description='点击次数')


class RpaElementInputRequest(RpaElementBaseRequest):
    """输入内容请求。"""

    value: str = Field(default='', description='要输入的文本')
    clear: bool = Field(default=True, description='输入前是否先清空')


class RpaElementTextRequest(RpaElementBaseRequest):
    """获取元素文本请求。"""

    pass


class RpaElementAttributeRequest(RpaElementBaseRequest):
    """获取元素属性请求。"""

    attributeName: str = Field(default='', description='属性名，如 href、src')


class RpaElementPressRequest(RpaElementBaseRequest):
    """键盘按键请求。"""

    key: str = Field(default='', description='按键名，如 Enter、Tab')


class RpaElementSelectRequest(RpaElementBaseRequest):
    """选择 <select> 选项请求。"""

    value: list[str] = Field(default_factory=list, description='待选 option value 列表')
    label: list[str] = Field(default_factory=list, description='待选 option 文本列表')
    index: list[int] = Field(default_factory=list, description='待选 option 索引列表')


class RpaElementOperationResponse(BaseModel):
    """元素操作响应。"""

    success: bool = True
    windowId: str | None = None
    pageId: str | None = None
    value: str | None = None
    values: list[str] | None = None
    exists: bool | None = None
    error: str | None = None


# ============================ locator ============================
class RpaLocatorItem(BaseModel):
    """定位器条件项——一个独立的定位维度。"""

    selector: str | None = Field(default=None, description='CSS/XPath 选择器')
    text: str | None = Field(default=None, description='元素可见文本，支持 get_by_text')
    attr: str | None = Field(default=None, description='属性名')
    attrValue: str | None = Field(default=None, description='属性值')
    role: str | None = Field(default=None, description='ARIA role，如 button、link')
    exact: bool = Field(default=False, description='是否精确匹配文本')
    nth: int | None = Field(default=None, description='第 N 个匹配元素，从 0 开始')
    has: list['RpaLocatorItem'] | None = Field(default=None, description='子元素条件')
    hasText: str | None = Field(default=None, description='子元素包含文本')
    operator: Literal['and', 'or', 'chain'] = Field(default='and', description='多条件组合方式')


class RpaLocatorFindRequest(RpaPageTarget):
    """批量查找元素请求。"""

    selectors: list[RpaLocatorItem] = Field(description='定位条件列表')
    minCount: int | None = Field(default=None, description='要求最少命中数量')
    maxCount: int | None = Field(default=None, description='要求最多命中数量')
    timeoutMs: int = Field(default=5000, ge=100, description='超时时间，毫秒')


class RpaLocatorDescribeRequest(RpaPageTarget):
    """描述单个元素请求。"""

    selectors: list[RpaLocatorItem] = Field(description='定位条件列表')
    timeoutMs: int = Field(default=5000, ge=100, description='超时时间，毫秒')


class RpaLocatorCountRequest(RpaPageTarget):
    """统计元素数量请求。"""

    selectors: list[RpaLocatorItem] = Field(description='定位条件列表')
    timeoutMs: int = Field(default=5000, ge=100, description='超时时间，毫秒')


class RpaLocatorLocatorResult(BaseModel):
    """单个定位元素描述。"""

    tagName: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    text: str | None = None
    innerHtml: str | None = None
    outerHtml: str | None = None
    boundingBox: dict[str, float] | None = None
    isVisible: bool | None = None
    isEnabled: bool | None = None
    isEditable: bool | None = None


class RpaLocatorFindResponse(BaseModel):
    """查找/描述/统计元素响应。"""

    success: bool = True
    count: int = 0
    elements: list[RpaLocatorLocatorResult] = Field(default_factory=list)
    error: str | None = None
    windowId: str | None = None
    pageId: str | None = None


class RpaLocatorCountResponse(BaseModel):
    """统计元素数量响应。"""

    success: bool = True
    count: int = 0
    error: str | None = None
    windowId: str | None = None
    pageId: str | None = None
