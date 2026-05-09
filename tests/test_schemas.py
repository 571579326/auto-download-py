import pytest
from pydantic import ValidationError

from app.schemas.common import Result
from app.schemas.browser import (
    BatchOpenPagesResponse,
    NewTabRequest,
    OpenUrlRequest,
    OpenWindowResponse,
    PageInfoResponse,
)
from app.schemas.desktop import (
    ClickImageRequest,
    ClickPositionRequest,
    HotkeyRequest,
    TypeTextRequest,
    WindowQueryRequest,
)
from app.schemas.rpa import (
    RpaFlowRunRequest,
    RpaFlowStep,
    RpaImageLocateRequest,
    RpaPageTarget,
    RpaWaitSleepRequest,
)


class TestResult:
    def test_default_values(self):
        r = Result(data="test")
        assert r.code == 0
        assert r.message == "ok"
        assert r.data == "test"

    def test_custom_values(self):
        r = Result(code=1, message="error", data=None)
        assert r.code == 1
        assert r.message == "error"
        assert r.data is None

    def test_generic_type(self):
        r = Result[dict](data={"key": "value"})
        assert r.data == {"key": "value"}


class TestBrowserSchemas:
    def test_open_window_response_required_fields(self):
        resp = OpenWindowResponse(
            windowId="w-001", status="1", userDataDir="/tmp", debugPort=9222
        )
        assert resp.windowId == "w-001"
        assert resp.sessionId is None

    def test_batch_open_pages_response(self):
        resp = BatchOpenPagesResponse(
            windowId="w-001", configCode="test", total=0, openedPages=[]
        )
        assert resp.total == 0
        assert resp.openedPages == []

    def test_new_tab_request_defaults(self):
        req = NewTabRequest()
        assert req.url == "about:blank"
        assert req.bringToFront is True

    def test_open_url_request_required_url(self):
        req = OpenUrlRequest(url="https://example.com")
        assert req.url == "https://example.com"
        assert req.newTab is False
        assert req.bringToFront is True

    def test_open_url_request_missing_url_raises(self):
        with pytest.raises(ValidationError):
            OpenUrlRequest()

    def test_page_info_response(self):
        resp = PageInfoResponse(
            windowId="w-001", pageId="p-001", pageIndex=1,
            title="Test", url="https://example.com", status="1"
        )
        assert resp.pageId == "p-001"


class TestDesktopSchemas:
    def test_click_image_request_defaults(self):
        req = ClickImageRequest(imagePath="test.png")
        assert req.confidence == 0.9
        assert req.clicks == 1
        assert req.timeoutMs == 5000
        assert req.retryIntervalMs == 400
        assert req.button == "left"
        assert req.grayscale is False

    def test_click_position_request_required(self):
        req = ClickPositionRequest(x=100, y=200)
        assert req.x == 100
        assert req.y == 200
        assert req.clicks == 1
        assert req.button == "left"

    def test_click_position_request_missing_raises(self):
        with pytest.raises(ValidationError):
            ClickPositionRequest()

    def test_type_text_request_required(self):
        req = TypeTextRequest(text="hello")
        assert req.text == "hello"
        assert req.intervalSeconds == 0.02

    def test_type_text_request_missing_raises(self):
        with pytest.raises(ValidationError):
            TypeTextRequest()

    def test_hotkey_request_required(self):
        req = HotkeyRequest(keys=["ctrl", "c"])
        assert req.keys == ["ctrl", "c"]

    def test_hotkey_request_missing_raises(self):
        with pytest.raises(ValidationError):
            HotkeyRequest()

    def test_window_query_request_defaults(self):
        req = WindowQueryRequest()
        assert req.backend == "uia"
        assert req.onlyVisible is True
        assert req.limit == 50


class TestRpaSchemas:
    def test_page_target_required_window_id(self):
        req = RpaPageTarget(windowId="w-001")
        assert req.windowId == "w-001"
        assert req.pageId is None
        assert req.urlContains is None

    def test_page_target_missing_window_id_raises(self):
        with pytest.raises(ValidationError):
            RpaPageTarget()

    def test_wait_sleep_request_seconds_validation(self):
        req = RpaWaitSleepRequest(seconds=5)
        assert req.seconds == 5

    def test_wait_sleep_request_negative_raises(self):
        with pytest.raises(ValidationError):
            RpaWaitSleepRequest(seconds=-1)

    def test_image_locate_request_confidence_range(self):
        req = RpaImageLocateRequest(imagePath="test.png", confidence=0.5)
        assert req.confidence == 0.5

    def test_image_locate_request_confidence_too_low(self):
        with pytest.raises(ValidationError):
            RpaImageLocateRequest(imagePath="test.png", confidence=0.05)

    def test_image_locate_request_confidence_too_high(self):
        with pytest.raises(ValidationError):
            RpaImageLocateRequest(imagePath="test.png", confidence=1.5)

    def test_flow_run_request_steps_required(self):
        step = RpaFlowStep(action="wait.sleep", params={"seconds": 1})
        req = RpaFlowRunRequest(steps=[step])
        assert len(req.steps) == 1
        assert req.windowId is None

    def test_flow_run_request_empty_steps(self):
        req = RpaFlowRunRequest(steps=[])
        assert len(req.steps) == 0
