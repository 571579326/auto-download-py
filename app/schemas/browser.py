from datetime import datetime

from pydantic import BaseModel, Field


class BingHuyaRequest(BaseModel):
    keyword: str = Field(default='虎牙直播lpl')
    targetPrefix: str = Field(default='https://www.huya.com')


class NewTabRequest(BaseModel):
    url: str = Field(default='about:blank')
    bringToFront: bool = Field(default=True)


class OpenUrlRequest(BaseModel):
    url: str
    pageId: str | None = None
    urlContains: str | None = None
    newTab: bool = False
    bringToFront: bool = True


class OpenConfiguredPagesRequest(BaseModel):
    configCode: str
    bringToFront: bool = True


class PageLocateRequest(BaseModel):
    pageId: str | None = None
    urlContains: str | None = None


class BatchOpenPageItem(BaseModel):
    url: str = Field(default='about:blank')
    active: bool = False


class OpenWindowResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    status: str
    userDataDir: str
    debugPort: int


class WindowSummary(BaseModel):
    windowId: str
    status: str
    lastPageTitle: str | None = None
    lastPageUrl: str | None = None
    createdTime: datetime | None = None
    updatedTime: datetime | None = None


class WindowListResponse(BaseModel):
    total: int
    windows: list[WindowSummary]


class PageSummary(BaseModel):
    pageId: str
    pageIndex: int
    title: str
    url: str
    status: str
    isActive: bool


class PageInfoResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    pageId: str
    pageIndex: int
    title: str
    url: str
    status: str


class PageListResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    total: int
    activePageId: str | None = None
    activePageIndex: int | None = None
    pages: list[PageSummary]


class BatchOpenPagesResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    configCode: str
    total: int
    openedPages: list[PageInfoResponse]


class ClosePageResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    pageId: str
    closed: bool
    remainingPages: int


class InvalidateWindowResponse(BaseModel):
    windowId: str
    sessionId: str | None = None
    status: str
    closed: bool


class ReopenWindowResponse(BaseModel):
    oldWindowId: str
    newWindowId: str
    status: str
    restoredPages: int
    closedOldWindow: bool
