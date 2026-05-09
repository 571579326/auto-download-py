from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================ page ============================
class RpaPageTarget(BaseModel):
    """RPA 页面定位参数。"""

    windowId: str = Field(description='浏览器窗口ID')
    pageId: str | None = Field(default=None, description='可选。页面ID')
    urlContains: str | None = Field(default=None, description='可选。URL 包含的关键字')


class RpaOpenUrlRequest(RpaPageTarget):
    url: str = Field(description='要打开的 URL')
    newTab: bool = Field(default=False, description='是否新开标签页')
    bringToFront: bool = Field(default=True, description='打开后是否切到前台')


class RpaOpenTabRequest(RpaPageTarget):
    url: str = Field(default='about:blank', description='新标签页 URL')
    bringToFront: bool = Field(default=True, description='是否切到前台')


class RpaPageWaitLoadStateRequest(RpaPageTarget):
    state: Literal['load', 'domcontentloaded', 'networkidle'] = Field(default='domcontentloaded')
    timeoutMs: int = Field(default=10000, ge=100)


class RpaPageReloadRequest(RpaPageTarget):
    waitUntil: Literal['load', 'domcontentloaded', 'networkidle'] = Field(default='domcontentloaded')
    timeoutMs: int = Field(default=10000, ge=100)


class RpaPageWaitUrlRequest(RpaPageTarget):
    urlContainsTarget: str = Field(description='等待 URL 中出现的关键字')
    timeoutMs: int = Field(default=10000, ge=100)
    retryIntervalMs: int = Field(default=300, ge=50)


class RpaScreenshotRequest(RpaPageTarget):
    path: str | None = Field(default=None)
    fullPage: bool = Field(default=True)


class RpaScreenshotResponse(BaseModel):
    success: bool
    path: str
    windowId: str
    pageId: str | None = None
    title: str | None = None
    url: str | None = None


# ============================ element ============================
class RpaElementBaseRequest(RpaPageTarget):
    selector: str | None = Field(default=None)
    text: str | None = Field(default=None)
    attr: str | None = Field(default=None)
    role: str | None = Field(default=None)
    exact: bool = Field(default=False)
    timeoutMs: int = Field(default=5000, ge=100)


class RpaElementClickRequest(RpaElementBaseRequest):
    clickCount: int = Field(default=1, ge=1)


class RpaElementInputRequest(RpaElementBaseRequest):
    value: str = Field(default='')
    clear: bool = Field(default=True)


class RpaElementTextRequest(RpaElementBaseRequest):
    pass


class RpaElementAttributeRequest(RpaElementBaseRequest):
    attributeName: str = Field(default='')


class RpaElementPressRequest(RpaElementBaseRequest):
    key: str = Field(default='')


class RpaElementSelectRequest(RpaElementBaseRequest):
    value: list[str] = Field(default_factory=list)
    label: list[str] = Field(default_factory=list)
    index: list[int] = Field(default_factory=list)


class RpaElementOperationResponse(BaseModel):
    success: bool = True
    windowId: str | None = None
    pageId: str | None = None
    value: str | None = None
    values: list[str] | None = None
    exists: bool | None = None
    error: str | None = None


# ============================ locator ============================
class RpaLocatorItem(BaseModel):
    selector: str | None = Field(default=None)
    text: str | None = Field(default=None)
    attr: str | None = Field(default=None)
    attrValue: str | None = Field(default=None)
    role: str | None = Field(default=None)
    exact: bool = Field(default=False)
    nth: int | None = Field(default=None)
    has: list['RpaLocatorItem'] | None = Field(default=None)
    hasText: str | None = Field(default=None)
    operator: Literal['and', 'or', 'chain'] = Field(default='and')


class RpaLocatorFindRequest(RpaPageTarget):
    selectors: list[RpaLocatorItem]
    minCount: int | None = Field(default=None)
    maxCount: int | None = Field(default=None)
    timeoutMs: int = Field(default=5000, ge=100)


class RpaLocatorDescribeRequest(RpaPageTarget):
    selectors: list[RpaLocatorItem]
    timeoutMs: int = Field(default=5000, ge=100)


class RpaLocatorCountRequest(RpaPageTarget):
    selectors: list[RpaLocatorItem]
    timeoutMs: int = Field(default=5000, ge=100)


class RpaLocatorLocatorResult(BaseModel):
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
    success: bool = True
    count: int = 0
    elements: list[RpaLocatorLocatorResult] = Field(default_factory=list)
    error: str | None = None
    windowId: str | None = None
    pageId: str | None = None


class RpaLocatorCountResponse(BaseModel):
    success: bool = True
    count: int = 0
    error: str | None = None
    windowId: str | None = None
    pageId: str | None = None


# ============================ image ============================
class RpaImageLocateRequest(BaseModel):
    imagePath: str
    confidence: float = Field(default=0.8, ge=0.1, le=1.0)
    regionLeft: int | None = Field(default=None)
    regionTop: int | None = Field(default=None)
    regionWidth: int | None = Field(default=None)
    regionHeight: int | None = Field(default=None)
    grayscale: bool = Field(default=False)
    timeoutMs: int = Field(default=5000, ge=100)
    retryIntervalMs: int = Field(default=500, ge=50)


class RpaImageLocateResponse(BaseModel):
    found: bool
    imagePath: str | None = None
    confidence: float | None = None
    centerX: int | None = None
    centerY: int | None = None
    left: int | None = None
    top: int | None = None
    width: int | None = None
    height: int | None = None
    error: str | None = None


class RpaImageClickRequest(RpaImageLocateRequest):
    clicks: int = Field(default=1, ge=1)
    intervalSeconds: float = Field(default=0.5, ge=0)
    button: str = Field(default='left')
    moveDurationSeconds: float = Field(default=0.5, ge=0)
    clickOffsetX: int = Field(default=0)
    clickOffsetY: int = Field(default=0)


class RpaImageClickManyRequest(RpaImageLocateRequest):
    imagePaths: list[str] = Field(default_factory=list)
    matchMode: Literal['OR', 'AND'] = Field(default='OR')


# ============================ mouse ============================
class RpaMouseClickRequest(BaseModel):
    x: int
    y: int
    clicks: int = Field(default=1, ge=1)
    intervalSeconds: float = Field(default=0.2, ge=0)
    button: str = Field(default='left')
    moveDurationSeconds: float = Field(default=0.3, ge=0)


class RpaMouseMoveRequest(BaseModel):
    x: int
    y: int
    durationSeconds: float = Field(default=0.5, ge=0)
    absolute: bool = Field(default=True)


class RpaMouseDragRequest(BaseModel):
    startX: int
    startY: int
    endX: int
    endY: int
    durationSeconds: float = Field(default=0.5, ge=0)
    button: str = Field(default='left')


class RpaMouseScrollRequest(BaseModel):
    clicks: int = Field(default=3)
    x: int | None = Field(default=None)
    y: int | None = Field(default=None)


class RpaMouseActionResponse(BaseModel):
    success: bool = True
    x: int | None = None
    y: int | None = None
    error: str | None = None


# ============================ keyboard ============================
class RpaKeyboardTypeRequest(BaseModel):
    text: str
    intervalSeconds: float = Field(default=0.05, ge=0)


class RpaKeyboardHotkeyRequest(BaseModel):
    keys: list[str]
    intervalSeconds: float = Field(default=0.1, ge=0)


class RpaKeyboardPressRequest(BaseModel):
    key: str
    presses: int = Field(default=1, ge=1)
    intervalSeconds: float = Field(default=0.1, ge=0)


class RpaKeyboardActionResponse(BaseModel):
    success: bool = True
    error: str | None = None


# ============================ clipboard ============================
class RpaClipboardSetRequest(BaseModel):
    text: str


class RpaClipboardResponse(BaseModel):
    success: bool = True
    text: str | None = None
    error: str | None = None


# ============================ data ============================
class RpaDataCondition(BaseModel):
    """数据筛选条件。"""

    column: str
    operator: Literal['==', '!=', '>', '<', '>=', '<=', 'contains', 'not_contains', 'startswith', 'endswith', 'in', 'not_in', 'regex']
    value: Any = None


class RpaDataSortField(BaseModel):
    """排序字段。"""

    column: str
    ascending: bool = Field(default=True)


class RpaDataRowsRequest(BaseModel):
    """传入行数据的基础请求。"""

    rows: list[dict] = Field(default_factory=list, description='二维表数据，每行为一条记录')
    columns: list[str] | None = Field(default=None, description='可选。列名列表，不传则从行数据自动推导')


class RpaDataCleanRequest(RpaDataRowsRequest):
    """数据清洗请求：去除空行/空列/重复行。"""

    dropEmptyRows: bool = Field(default=True)
    dropEmptyColumns: bool = Field(default=True)
    dropDuplicates: bool = Field(default=True)
    stripWhitespace: bool = Field(default=True)
    fillNa: Any = Field(default='', description='空值填充内容')


class RpaDataFilterRequest(RpaDataRowsRequest):
    """数据筛选请求。"""

    conditions: list[RpaDataCondition] = Field(default_factory=list)
    logic: Literal['and', 'or'] = Field(default='and')


class RpaDataSortRequest(RpaDataRowsRequest):
    """数据排序请求。"""

    sortBy: list[RpaDataSortField] = Field(default_factory=list)


class RpaDataUniqueRequest(RpaDataRowsRequest):
    """去重请求。"""

    subset: list[str] | None = Field(default=None, description='按指定列去重')
    keep: Literal['first', 'last', 'none'] = Field(default='first')


class RpaDataGroupCountRequest(RpaDataRowsRequest):
    """分组计数请求。"""

    groupBy: list[str] = Field(default_factory=list)


class RpaDataExtractRegexRequest(RpaDataRowsRequest):
    """正则提取请求。"""

    column: str
    pattern: str
    outputColumn: str = Field(default='extracted')
    caseSensitive: bool = Field(default=True)


class RpaDataFileReadRequest(BaseModel):
    """文件读取请求。"""

    path: str
    sheetName: str | None = Field(default=None)
    hasHeader: bool = Field(default=True)
    encoding: str = Field(default='utf-8')
    delimiter: str = Field(default=',')


class RpaDataFileWriteRequest(RpaDataRowsRequest):
    """文件写入请求。"""

    path: str
    sheetName: str = Field(default='Sheet1')
    includeHeader: bool = Field(default=True)
    encoding: str = Field(default='utf-8')
    writeMode: Literal['overwrite', 'append'] = Field(default='overwrite')


class RpaDataTableResponse(BaseModel):
    """表格数据响应。"""

    success: bool = True
    rowCount: int = 0
    columns: list[str] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    error: str | None = None


class RpaDataValueResponse(BaseModel):
    """单值数据响应。"""

    success: bool = True
    value: Any = None
    values: list[Any] | None = None
    error: str | None = None


# ============================ wait ============================
class RpaWaitSleepRequest(BaseModel):
    """等待指定秒数请求。"""

    seconds: float = Field(default=1, ge=0)


# ============================ assert ============================
class RpaAssertResponse(BaseModel):
    """断言结果。"""

    success: bool
    expected: str | None = None
    actual: str | None = None
    error: str | None = None


# ============================ flow ============================
class RpaFlowStep(BaseModel):
    """流程步骤定义。"""

    action: str = Field(description='动作名，如 page.open-url、element.click')
    name: str | None = Field(default=None, description='步骤别名')
    params: dict = Field(default_factory=dict, description='动作参数')
    onFailure: Literal['stop', 'continue', 'ignore'] = Field(default='stop')
    retryTimes: int = Field(default=0, ge=0)
    retryDelayMs: int = Field(default=1000)


class RpaFlowRunRequest(BaseModel):
    """流程执行请求。"""

    steps: list[RpaFlowStep]
    windowId: str | None = Field(default=None)
    pageId: str | None = Field(default=None)

    class Config:
        title = 'RpaFlowRunRequest'
        json_schema_extra = {
            'example': {
                'steps': [
                    {'action': 'page.open-url', 'params': {'url': 'https://example.com'}},
                    {'action': 'wait.sleep', 'params': {'seconds': 2}},
                    {'action': 'element.click', 'params': {'selector': '#submit'}},
                ],
            },
        }


class RpaFlowStepResult(BaseModel):
    """单步执行结果。"""

    stepIndex: int
    action: str
    name: str | None = None
    success: bool
    durationMs: float
    data: Any = None
    error: str | None = None


class RpaFlowRunResponse(BaseModel):
    """流程执行响应。"""

    success: bool
    totalSteps: int
    succeeded: int
    failed: int
    results: list[RpaFlowStepResult] = Field(default_factory=list)
    totalDurationMs: float = 0
    error: str | None = None
