import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.schemas.browser import (
    BatchOpenPagesResponse,
    OpenWindowResponse,
    PageInfoResponse,
)
from app.schemas.desktop import ClickImageRequest, ClickImageResponse

client = TestClient(app)

IMAGE_PATH = "app/visual/templates/cf_check_dark.png"
CONFIG_CODE = "acg18"
BASE_URL = "/auto-download"


def _mock_batch_open_response():
    return BatchOpenPagesResponse(
        windowId="test-window-001",
        sessionId="test-window-001",
        configCode=CONFIG_CODE,
        total=1,
        openedPages=[
            PageInfoResponse(
                windowId="test-window-001",
                sessionId="test-window-001",
                pageId="page-1",
                pageIndex=1,
                title="Test Page",
                url="https://hxcy.top/",
                status="1",
            )
        ],
    )


class TestPageFlowAPI:
    @patch("app.services.business_common_service.business_image_click_service.find_and_click_images")
    @patch("app.services.business_common_service.business_image_click_service.build_auto_click_options")
    @patch("app.services.business_common_service.browser_service.open_config_pages_playwright_once")
    def test_page_flow_full_success(
        self, mock_open_config, mock_build_options, mock_find_click
    ):
        from app.services.business_image_click_service import BusinessImageClickOptions, BusinessImageClickResult

        mock_open_config.return_value = _mock_batch_open_response()
        mock_build_options.return_value = BusinessImageClickOptions(
            enabled=True,
            image_paths=[IMAGE_PATH],
            match_mode="or",
            confidence=0.8,
        )
        mock_find_click.return_value = BusinessImageClickResult(
            clicked=True,
            skipped=False,
            image_paths=[IMAGE_PATH],
            match_mode="or",
            clicked_images=[{"imagePath": IMAGE_PATH, "clicked": True}],
        )

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={"configCode": CONFIG_CODE},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["configCode"] == CONFIG_CODE
        assert data["data"]["pagesOpened"] == 1
        assert data["data"]["imageClicked"] is True

    @patch("app.services.business_common_service.business_image_click_service.find_and_click_images")
    @patch("app.services.business_common_service.business_image_click_service.build_auto_click_options")
    @patch("app.services.business_common_service.browser_service.open_config_pages_playwright_once")
    def test_page_flow_image_not_found(
        self, mock_open_config, mock_build_options, mock_find_click
    ):
        from app.services.business_image_click_service import BusinessImageClickOptions, BusinessImageClickResult

        mock_open_config.return_value = _mock_batch_open_response()
        mock_build_options.return_value = BusinessImageClickOptions(
            enabled=True,
            image_paths=[IMAGE_PATH],
            match_mode="or",
            confidence=0.8,
        )
        mock_find_click.return_value = BusinessImageClickResult(
            clicked=False,
            skipped=False,
            image_paths=[IMAGE_PATH],
            match_mode="or",
            error="timeout",
        )

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={"configCode": CONFIG_CODE},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["imageClicked"] is False
        assert data["data"]["pagesOpened"] == 1

    @patch("app.services.business_common_service.business_image_click_service.find_and_click_images")
    @patch("app.services.business_common_service.business_image_click_service.build_auto_click_options")
    @patch("app.services.business_common_service.browser_service.open_config_pages_playwright_once")
    def test_page_flow_image_skipped_disabled(
        self, mock_open_config, mock_build_options, mock_find_click
    ):
        from app.services.business_image_click_service import BusinessImageClickOptions, BusinessImageClickResult

        mock_open_config.return_value = _mock_batch_open_response()
        mock_build_options.return_value = BusinessImageClickOptions(
            enabled=False,
            image_paths=[],
            match_mode="or",
        )
        mock_find_click.return_value = BusinessImageClickResult(
            clicked=False,
            skipped=True,
            image_paths=[],
            match_mode="or",
            skip_reason="auto_click_disabled",
        )

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={"configCode": CONFIG_CODE},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["imageClicked"] is False
        assert data["data"]["imageClickSkipped"] is True

    @patch("app.services.business_common_service.browser_service.open_config_pages_playwright_once")
    def test_page_flow_browser_open_failure(self, mock_open_config):
        mock_open_config.side_effect = RuntimeError("无法启动浏览器")

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={"configCode": CONFIG_CODE},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == 500

    @patch("app.services.business_common_service.browser_service.open_config_pages_playwright_once")
    def test_page_flow_config_not_found(self, mock_open_config):
        mock_open_config.side_effect = ValueError(
            "no valid page config found: configCode=unknown"
        )

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={"configCode": "unknown"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400


class TestClickImageIfExists:
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_success(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=500, centerY=300,
            left=480, top=280, width=40, height=40,
            imagePath=IMAGE_PATH, confidence=0.85,
        )

        result = click_image_if_exists(image_path=IMAGE_PATH, confidence=0.8)

        assert result is True
        mock_click.assert_called_once()
        call_arg = mock_click.call_args[0][0]
        assert isinstance(call_arg, ClickImageRequest)
        assert call_arg.imagePath == IMAGE_PATH
        assert call_arg.confidence == 0.8

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_failure(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.side_effect = RuntimeError("图像未找到")

        result = click_image_if_exists(image_path=IMAGE_PATH, confidence=0.9)
        assert result is False

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_with_error_handler(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.side_effect = RuntimeError("图像检测失败")
        handler_called = []

        def error_handler(exc):
            handler_called.append(str(exc))

        result = click_image_if_exists(
            image_path=IMAGE_PATH, confidence=0.9, error_handler=error_handler,
        )

        assert result is False
        assert len(handler_called) == 1
        assert "图像检测失败" in handler_called[0]

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_with_error_handler_exception(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.side_effect = RuntimeError("图像检测失败")

        def bad_handler(exc):
            raise RuntimeError("handler自身报错")

        result = click_image_if_exists(
            image_path=IMAGE_PATH, confidence=0.9, error_handler=bad_handler,
        )
        assert result is False

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_custom_timeout_and_retry(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=100, centerY=200,
            left=90, top=190, width=20, height=20,
            imagePath=IMAGE_PATH, confidence=0.95,
        )

        result = click_image_if_exists(
            image_path=IMAGE_PATH, confidence=0.85,
            timeout_ms=3000, retry_interval_ms=200,
        )

        assert result is True
        call_arg = mock_click.call_args[0][0]
        assert call_arg.timeoutMs == 3000
        assert call_arg.retryIntervalMs == 200


class TestScreenManagerClickImage:
    @patch("os.path.exists", return_value=True)
    @patch("app.visual.screen_manager.ScreenManager._pyautogui")
    def test_click_image_success(self, mock_pyautogui_get, mock_exists):
        from app.visual.screen_manager import ScreenManager
        from app.schemas.desktop import ClickImageRequest

        mock_pyautogui = MagicMock()
        mock_pyautogui.FAILSAFE = True
        mock_box = MagicMock()
        mock_box.left = 100
        mock_box.top = 200
        mock_box.width = 50
        mock_box.height = 50
        mock_pyautogui.locateOnScreen.return_value = mock_box
        mock_pyautogui.center.return_value = MagicMock(x=125, y=225)
        mock_pyautogui_get.return_value = mock_pyautogui

        screen_manager = ScreenManager()
        request = ClickImageRequest(
            imagePath=IMAGE_PATH, confidence=0.8,
            timeoutMs=5000, retryIntervalMs=400,
        )

        result = screen_manager.click_image(request)

        assert result.clicked is True
        assert result.centerX == 125
        assert result.centerY == 225
        mock_pyautogui.locateOnScreen.assert_called_once_with(
            IMAGE_PATH, confidence=0.8, region=None, grayscale=False,
        )
        mock_pyautogui.click.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("app.visual.screen_manager.ScreenManager._pyautogui")
    def test_click_image_timeout(self, mock_pyautogui_get, mock_exists):
        from app.visual.screen_manager import ScreenManager
        from app.schemas.desktop import ClickImageRequest

        mock_pyautogui = MagicMock()
        mock_pyautogui.FAILSAFE = True
        mock_pyautogui.locateOnScreen.return_value = None
        mock_pyautogui_get.return_value = mock_pyautogui

        screen_manager = ScreenManager()
        request = ClickImageRequest(
            imagePath=IMAGE_PATH, confidence=0.9,
            timeoutMs=500, retryIntervalMs=100,
        )

        with pytest.raises(RuntimeError, match="超时未找到目标图片"):
            screen_manager.click_image(request)

    @patch("os.path.exists", return_value=False)
    def test_click_image_path_not_found(self, mock_exists):
        from app.visual.screen_manager import ScreenManager
        from app.schemas.desktop import ClickImageRequest

        screen_manager = ScreenManager()
        request = ClickImageRequest(imagePath="nonexistent.png", confidence=0.9)

        with pytest.raises(ValueError, match="imagePath不存在"):
            screen_manager.click_image(request)

    @patch("os.path.exists", return_value=True)
    @patch("app.visual.screen_manager.ScreenManager._pyautogui")
    def test_click_image_with_region(self, mock_pyautogui_get, mock_exists):
        from app.visual.screen_manager import ScreenManager
        from app.schemas.desktop import ClickImageRequest

        mock_pyautogui = MagicMock()
        mock_pyautogui.FAILSAFE = True
        mock_box = MagicMock()
        mock_box.left = 200
        mock_box.top = 300
        mock_box.width = 30
        mock_box.height = 30
        mock_pyautogui.locateOnScreen.return_value = mock_box
        mock_pyautogui.center.return_value = MagicMock(x=215, y=315)
        mock_pyautogui_get.return_value = mock_pyautogui

        screen_manager = ScreenManager()
        request = ClickImageRequest(
            imagePath=IMAGE_PATH, confidence=0.85,
            regionLeft=0, regionTop=0, regionWidth=1920, regionHeight=1080,
            grayscale=True,
        )

        result = screen_manager.click_image(request)

        assert result.clicked is True
        call_kwargs = mock_pyautogui.locateOnScreen.call_args
        assert call_kwargs[1]["region"] == (0, 0, 1920, 1080)
        assert call_kwargs[1]["grayscale"] is True
        assert call_kwargs[1]["confidence"] == 0.85
