import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

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


class TestPageFlowAPI:
    """page-flow API 端点的单元测试"""

    def _mock_open_window_response(self):
        return OpenWindowResponse(
            windowId="test-window-001",
            sessionId="test-window-001",
            status="1",
            userDataDir="C:/chrome_debug_profile",
            debugPort=9222,
        )

    def _mock_batch_open_response(self):
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
                    title="幻想次元_首页",
                    url="https://hxcy.top/",
                    status="1",
                )
            ],
        )

    def _mock_image_click_response(self, clicked=True):
        if clicked:
            return ClickImageResponse(
                clicked=True,
                centerX=500,
                centerY=300,
                left=480,
                top=280,
                width=40,
                height=40,
                imagePath=IMAGE_PATH,
                confidence=0.85,
            )
        raise RuntimeError("图像未找到")

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_page_flow_full_success(
        self, mock_click_image, mock_open_config, mock_open_browser
    ):
        """测试完整的 page-flow 流程：打开浏览器 -> 按配置打开页面 -> 检测并点击图像 -> 全部成功"""
        mock_open_browser.return_value = self._mock_open_window_response()
        mock_open_config.return_value = self._mock_batch_open_response()
        mock_click_image.return_value = self._mock_image_click_response(clicked=True)

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": CONFIG_CODE,
                "imagePath": IMAGE_PATH,
                "imageConfidence": 0.8,
                "pageStabilizeSeconds": 1.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "pageFlow 执行成功"
        assert data["data"]["configCode"] == CONFIG_CODE
        assert data["data"]["windowId"] == "test-window-001"
        assert data["data"]["pagesOpened"] == 1
        assert data["data"]["imageClicked"] is True

        mock_open_browser.assert_called_once()
        mock_open_config.assert_called_once()
        mock_click_image.assert_called_once()

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_page_flow_image_not_found(
        self, mock_click_image, mock_open_config, mock_open_browser
    ):
        """测试流程：图像未找到时，返回 imageClicked=False 但不报错"""
        mock_open_browser.return_value = self._mock_open_window_response()
        mock_open_config.return_value = self._mock_batch_open_response()
        mock_click_image.side_effect = RuntimeError("图像未找到")

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": CONFIG_CODE,
                "imagePath": IMAGE_PATH,
                "imageConfidence": 0.8,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["imageClicked"] is False
        assert data["data"]["pagesOpened"] == 1

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    def test_page_flow_without_image(
        self, mock_open_config, mock_open_browser
    ):
        """测试流程：不传 imagePath 时，仅打开页面不检测图像"""
        mock_open_browser.return_value = self._mock_open_window_response()
        mock_open_config.return_value = self._mock_batch_open_response()

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": CONFIG_CODE,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["imageClicked"] is False
        assert data["data"]["pagesOpened"] == 1

    @patch("app.services.business_service.browser_service.open_browser")
    def test_page_flow_browser_open_failure(self, mock_open_browser):
        """测试流程：浏览器打开失败时应返回 500"""
        mock_open_browser.side_effect = RuntimeError("无法启动浏览器")

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": CONFIG_CODE,
                "imagePath": IMAGE_PATH,
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == 500

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    def test_page_flow_config_not_found(
        self, mock_open_config, mock_open_browser
    ):
        """测试流程：configCode 对应的配置不存在时应返回 400（ValueError）"""
        mock_open_browser.return_value = self._mock_open_window_response()
        mock_open_config.side_effect = ValueError(
            "no valid page config found: configCode=unknown"
        )

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": "unknown",
                "imagePath": IMAGE_PATH,
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_page_flow_confidence_80_percent(
        self, mock_click_image, mock_open_config, mock_open_browser
    ):
        """测试流程：相似度阈值设为 0.8 (>80%)"""
        mock_open_browser.return_value = self._mock_open_window_response()
        mock_open_config.return_value = self._mock_batch_open_response()
        mock_click_image.return_value = self._mock_image_click_response(clicked=True)

        response = client.post(
            f"{BASE_URL}/biz/page-flow",
            params={
                "configCode": CONFIG_CODE,
                "imagePath": IMAGE_PATH,
                "imageConfidence": 0.8,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["imageClicked"] is True

        call_args = mock_click_image.call_args[0][0]
        assert call_args.confidence == 0.8


class TestBusinessService:
    """BusinessService.open_pages_and_check_image 的单元测试"""

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    @patch("app.services.business_service.click_image_if_exists")
    def test_full_flow_success(
        self, mock_click_if_exists, mock_open_config, mock_open_browser
    ):
        from app.services.business_service import business_service
        from app.schemas.browser import OpenWindowResponse, BatchOpenPagesResponse, PageInfoResponse

        mock_open_browser.return_value = OpenWindowResponse(
            windowId="w-001", sessionId="w-001", status="1",
            userDataDir="/tmp/profile", debugPort=9222,
        )
        mock_open_config.return_value = BatchOpenPagesResponse(
            windowId="w-001", sessionId="w-001", configCode=CONFIG_CODE,
            total=1,
            openedPages=[
                PageInfoResponse(
                    windowId="w-001", sessionId="w-001", pageId="page-1",
                    pageIndex=1, title="Test", url="https://hxcy.top/", status="1",
                )
            ],
        )
        mock_click_if_exists.return_value = True

        result = business_service.open_pages_and_check_image(
            config_code=CONFIG_CODE,
            image_path=IMAGE_PATH,
            image_confidence=0.8,
        )

        assert result["configCode"] == CONFIG_CODE
        assert result["windowId"] == "w-001"
        assert result["pagesOpened"] == 1
        assert result["imageClicked"] is True

        mock_click_if_exists.assert_called_once_with(
            image_path=IMAGE_PATH,
            confidence=0.8,
            error_handler=None,
        )

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    @patch("app.services.business_service.click_image_if_exists")
    def test_flow_image_not_clicked(
        self, mock_click_if_exists, mock_open_config, mock_open_browser
    ):
        from app.services.business_service import business_service
        from app.schemas.browser import OpenWindowResponse, BatchOpenPagesResponse, PageInfoResponse

        mock_open_browser.return_value = OpenWindowResponse(
            windowId="w-001", sessionId="w-001", status="1",
            userDataDir="/tmp/profile", debugPort=9222,
        )
        mock_open_config.return_value = BatchOpenPagesResponse(
            windowId="w-001", sessionId="w-001", configCode=CONFIG_CODE,
            total=1,
            openedPages=[
                PageInfoResponse(
                    windowId="w-001", sessionId="w-001", pageId="page-1",
                    pageIndex=1, title="Test", url="https://hxcy.top/", status="1",
                )
            ],
        )
        mock_click_if_exists.return_value = False

        result = business_service.open_pages_and_check_image(
            config_code=CONFIG_CODE,
            image_path=IMAGE_PATH,
            image_confidence=0.9,
        )

        assert result["imageClicked"] is False

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.open_config_pages")
    def test_flow_no_image_path(self, mock_open_config, mock_open_browser):
        from app.services.business_service import business_service
        from app.schemas.browser import OpenWindowResponse, BatchOpenPagesResponse, PageInfoResponse

        mock_open_browser.return_value = OpenWindowResponse(
            windowId="w-001", sessionId="w-001", status="1",
            userDataDir="/tmp/profile", debugPort=9222,
        )
        mock_open_config.return_value = BatchOpenPagesResponse(
            windowId="w-001", sessionId="w-001", configCode=CONFIG_CODE,
            total=1,
            openedPages=[
                PageInfoResponse(
                    windowId="w-001", sessionId="w-001", pageId="page-1",
                    pageIndex=1, title="Test", url="https://hxcy.top/", status="1",
                )
            ],
        )

        result = business_service.open_pages_and_check_image(
            config_code=CONFIG_CODE,
            image_path=None,
        )

        assert result["imageClicked"] is False
        assert result["pagesOpened"] == 1

    @patch("app.services.business_service.browser_service.open_browser")
    @patch("app.services.business_service.browser_service.close_browser")
    def test_flow_config_error_closes_window(
        self, mock_close_browser, mock_open_browser
    ):
        from app.services.business_service import business_service
        from app.schemas.browser import OpenWindowResponse

        mock_open_browser.return_value = OpenWindowResponse(
            windowId="w-001", sessionId="w-001", status="1",
            userDataDir="/tmp/profile", debugPort=9222,
        )

        with patch("app.services.business_service.browser_service.open_config_pages") as mock_config:
            mock_config.side_effect = ValueError("no valid page config")
            with pytest.raises(ValueError):
                business_service.open_pages_and_check_image(
                    config_code="invalid",
                    image_path=IMAGE_PATH,
                )

        mock_close_browser.assert_called_once_with("w-001")


class TestClickImageIfExists:
    """click_image_if_exists 工具函数的单元测试"""

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_success(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=500, centerY=300,
            left=480, top=280, width=40, height=40,
            imagePath=IMAGE_PATH, confidence=0.85,
        )

        result = click_image_if_exists(
            image_path=IMAGE_PATH,
            confidence=0.8,
        )

        assert result is True
        mock_click.assert_called_once()
        call_arg = mock_click.call_args[0][0]
        assert isinstance(call_arg, ClickImageRequest)
        assert call_arg.imagePath == IMAGE_PATH
        assert call_arg.confidence == 0.8
        assert call_arg.timeoutMs == 5000
        assert call_arg.retryIntervalMs == 400
        assert call_arg.clicks == 1
        assert call_arg.button == "left"

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_failure(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.side_effect = RuntimeError("图像未找到")

        result = click_image_if_exists(
            image_path=IMAGE_PATH,
            confidence=0.9,
        )

        assert result is False

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_click_with_error_handler(self, mock_click):
        from app.utils.image_utils import click_image_if_exists

        mock_click.side_effect = RuntimeError("图像检测失败")
        handler_called = []

        def error_handler(exc):
            handler_called.append(str(exc))

        result = click_image_if_exists(
            image_path=IMAGE_PATH,
            confidence=0.9,
            error_handler=error_handler,
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
            image_path=IMAGE_PATH,
            confidence=0.9,
            error_handler=bad_handler,
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
            image_path=IMAGE_PATH,
            confidence=0.85,
            timeout_ms=3000,
            retry_interval_ms=200,
        )

        assert result is True
        call_arg = mock_click.call_args[0][0]
        assert call_arg.timeoutMs == 3000
        assert call_arg.retryIntervalMs == 200


class TestScreenManagerClickImage:
    """ScreenManager.click_image 的单元测试"""

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
            imagePath=IMAGE_PATH,
            confidence=0.8,
            timeoutMs=5000,
            retryIntervalMs=400,
        )

        result = screen_manager.click_image(request)

        assert result.clicked is True
        assert result.centerX == 125
        assert result.centerY == 225
        mock_pyautogui.locateOnScreen.assert_called_once_with(
            IMAGE_PATH,
            confidence=0.8,
            region=None,
            grayscale=False,
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
            imagePath=IMAGE_PATH,
            confidence=0.9,
            timeoutMs=500,
            retryIntervalMs=100,
        )

        with pytest.raises(RuntimeError, match="超时未找到目标图片"):
            screen_manager.click_image(request)

    @patch("os.path.exists", return_value=False)
    def test_click_image_path_not_found(self, mock_exists):
        from app.visual.screen_manager import ScreenManager
        from app.schemas.desktop import ClickImageRequest

        screen_manager = ScreenManager()
        request = ClickImageRequest(
            imagePath="nonexistent.png",
            confidence=0.9,
        )

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
            imagePath=IMAGE_PATH,
            confidence=0.85,
            regionLeft=0,
            regionTop=0,
            regionWidth=1920,
            regionHeight=1080,
            grayscale=True,
        )

        result = screen_manager.click_image(request)

        assert result.clicked is True
        mock_pyautogui.locateOnScreen.assert_called_once()
        call_kwargs = mock_pyautogui.locateOnScreen.call_args
        assert call_kwargs[1]["region"] == (0, 0, 1920, 1080)
        assert call_kwargs[1]["grayscale"] is True
        assert call_kwargs[1]["confidence"] == 0.85
