from pydantic import BaseModel, Field


class WindowQueryRequest(BaseModel):
    backend: str = Field(default='uia')
    titleContains: str | None = None
    titleRegex: str | None = None
    onlyVisible: bool = True
    limit: int = 50


class WindowInfo(BaseModel):
    handle: int
    title: str
    className: str | None = None
    processId: int | None = None
    isVisible: bool = True


class WindowListResponse(BaseModel):
    total: int
    windows: list[WindowInfo]


class ActivateWindowRequest(BaseModel):
    backend: str = Field(default='uia')
    handle: int | None = None
    title: str | None = None
    titleRegex: str | None = None
    className: str | None = None
    timeoutMs: int = 5000
    restoreIfMinimized: bool = True


class ActivateWindowResponse(BaseModel):
    activated: bool
    handle: int
    title: str


class ClickPositionRequest(BaseModel):
    x: int
    y: int
    clicks: int = 1
    intervalSeconds: float = 0.0
    button: str = 'left'
    durationSeconds: float = 0.0


class ClickPositionResponse(BaseModel):
    clicked: bool
    x: int
    y: int
    clicks: int
    button: str


class ClickImageRequest(BaseModel):
    imagePath: str
    confidence: float = 0.9
    regionLeft: int | None = None
    regionTop: int | None = None
    regionWidth: int | None = None
    regionHeight: int | None = None
    grayscale: bool = False
    clicks: int = 1
    intervalSeconds: float = 0.0
    button: str = 'left'
    timeoutMs: int = 5000
    retryIntervalMs: int = 400
    moveDurationSeconds: float = 0.0


class ClickImageResponse(BaseModel):
    clicked: bool
    centerX: int
    centerY: int
    left: int
    top: int
    width: int
    height: int
    imagePath: str
    confidence: float


class TypeTextRequest(BaseModel):
    text: str
    intervalSeconds: float = 0.02


class KeyboardActionResponse(BaseModel):
    success: bool
    message: str


class HotkeyRequest(BaseModel):
    keys: list[str]
    intervalSeconds: float = 0.0


class OcrClickTextRequest(BaseModel):
    text: str
    contains: bool = True
    confidence: float = 0.5
    timeoutMs: int = 5000
    retryIntervalMs: int = 400


class OcrClickTextResponse(BaseModel):
    reserved: bool
    message: str
