from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.desktop import (
    ActivateWindowResponse,
    ClickImageResponse,
    ClickImagesResponse,
    ClickPositionResponse,
    KeyboardActionResponse,
    OcrClickTextResponse,
    WindowInfo,
    WindowListResponse,
)

client = TestClient(app)
BASE_URL = '/auto-download/desktop'


def _make_window_list_response():
    return WindowListResponse(
        total=1,
        windows=[
            WindowInfo(
                handle=12345,
                title='Test Window',
                className='TestClass',
                processId=1234,
                isVisible=True,
            )
        ],
    )


def _make_activate_window_response():
    return ActivateWindowResponse(
        activated=True,
        handle=12345,
        title='Test Window',
    )


def _make_click_position_response():
    return ClickPositionResponse(
        clicked=True,
        x=100,
        y=200,
        clicks=1,
        button='left',
    )


def _make_click_image_response():
    return ClickImageResponse(
        clicked=True,
        centerX=500,
        centerY=300,
        left=480,
        top=280,
        width=40,
        height=40,
        imagePath='test.png',
        confidence=0.9,
    )


def _make_click_images_response():
    return ClickImagesResponse(
        clicked=True,
        matchMode='or',
        clickedImages=[_make_click_image_response()],
    )


def _make_ocr_click_text_response():
    return OcrClickTextResponse(
        reserved=True,
        message='预留接口',
    )


def _make_keyboard_action_response():
    return KeyboardActionResponse(
        success=True,
        message='完成',
    )


class TestListWindows:
    @patch('app.api.desktop.desktop_service')
    def test_list_windows_returns_window_list(self, mock_desktop_service):
        mock_desktop_service.list_windows.return_value = _make_window_list_response()

        response = client.get(
            f'{BASE_URL}/windows',
            params={
                'backend': 'uia',
                'titleContains': 'Test',
                'onlyVisible': True,
                'limit': 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['total'] == 1
        assert data['data']['windows'][0]['handle'] == 12345
        assert data['data']['windows'][0]['title'] == 'Test Window'
        assert data['data']['windows'][0]['className'] == 'TestClass'
        assert data['data']['windows'][0]['processId'] == 1234
        assert data['data']['windows'][0]['isVisible'] is True
        mock_desktop_service.list_windows.assert_called_once()

    @patch('app.api.desktop.desktop_service')
    def test_list_windows_with_title_regex(self, mock_desktop_service):
        mock_desktop_service.list_windows.return_value = _make_window_list_response()

        response = client.get(
            f'{BASE_URL}/windows',
            params={
                'backend': 'uia',
                'titleRegex': '.*Test.*',
                'onlyVisible': True,
                'limit': 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['data']['total'] == 1
        mock_desktop_service.list_windows.assert_called_once()

    @patch('app.api.desktop.desktop_service')
    def test_list_windows_default_params(self, mock_desktop_service):
        mock_desktop_service.list_windows.return_value = _make_window_list_response()

        response = client.get(f'{BASE_URL}/windows')

        assert response.status_code == 200
        data = response.json()
        assert data['data']['total'] == 1
        call_args = mock_desktop_service.list_windows.call_args[0][0]
        assert call_args.backend == 'uia'
        assert call_args.onlyVisible is True
        assert call_args.limit == 50


class TestActivateWindow:
    @patch('app.api.desktop.desktop_service')
    def test_activate_window_success(self, mock_desktop_service):
        mock_desktop_service.activate_window.return_value = _make_activate_window_response()

        response = client.post(
            f'{BASE_URL}/window/activate',
            json={
                'handle': 12345,
                'title': 'Test Window',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['activated'] is True
        assert data['data']['handle'] == 12345
        assert data['data']['title'] == 'Test Window'
        mock_desktop_service.activate_window.assert_called_once()


class TestClickPosition:
    @patch('app.api.desktop.visual_service')
    def test_click_position_success(self, mock_visual_service):
        mock_visual_service.click_position.return_value = _make_click_position_response()

        response = client.post(
            f'{BASE_URL}/click/pos',
            json={
                'x': 100,
                'y': 200,
                'clicks': 1,
                'button': 'left',
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['clicked'] is True
        assert data['data']['x'] == 100
        assert data['data']['y'] == 200
        assert data['data']['clicks'] == 1
        assert data['data']['button'] == 'left'
        mock_visual_service.click_position.assert_called_once()


class TestClickImage:
    @patch('app.api.desktop.visual_service')
    def test_click_image_success(self, mock_visual_service):
        mock_visual_service.click_image.return_value = _make_click_image_response()

        response = client.post(
            f'{BASE_URL}/click/image',
            json={
                'imagePath': 'test.png',
                'confidence': 0.9,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['clicked'] is True
        assert data['data']['centerX'] == 500
        assert data['data']['centerY'] == 300
        assert data['data']['left'] == 480
        assert data['data']['top'] == 280
        assert data['data']['width'] == 40
        assert data['data']['height'] == 40
        assert data['data']['imagePath'] == 'test.png'
        assert data['data']['confidence'] == 0.9
        mock_visual_service.click_image.assert_called_once()


class TestClickImages:
    @patch('app.api.desktop.visual_service')
    def test_click_images_success(self, mock_visual_service):
        mock_visual_service.click_images.return_value = _make_click_images_response()

        response = client.post(
            f'{BASE_URL}/click/images',
            json={
                'imagePaths': ['test.png'],
                'matchMode': 'or',
                'confidence': 0.9,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['clicked'] is True
        assert data['data']['matchMode'] == 'or'
        assert len(data['data']['clickedImages']) == 1
        assert data['data']['clickedImages'][0]['centerX'] == 500
        assert data['data']['clickedImages'][0]['centerY'] == 300
        mock_visual_service.click_images.assert_called_once()


class TestClickOcrText:
    @patch('app.api.desktop.visual_service')
    def test_click_ocr_text_reserved(self, mock_visual_service):
        mock_visual_service.ocr_click_text_reserved.return_value = _make_ocr_click_text_response()

        response = client.post(
            f'{BASE_URL}/click/ocr-text',
            json={
                'text': 'verify',
                'contains': True,
                'confidence': 0.5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['reserved'] is True
        assert data['data']['message'] == '预留接口'
        mock_visual_service.ocr_click_text_reserved.assert_called_once()


class TestTypeText:
    @patch('app.api.desktop.desktop_service')
    def test_type_text_success(self, mock_desktop_service):
        mock_desktop_service.type_text.return_value = _make_keyboard_action_response()

        response = client.post(
            f'{BASE_URL}/keyboard/type',
            json={
                'text': 'hello',
                'intervalSeconds': 0.02,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['success'] is True
        assert data['data']['message'] == '完成'
        mock_desktop_service.type_text.assert_called_once()


class TestHotkey:
    @patch('app.api.desktop.desktop_service')
    def test_hotkey_success(self, mock_desktop_service):
        mock_desktop_service.hotkey.return_value = _make_keyboard_action_response()

        response = client.post(
            f'{BASE_URL}/keyboard/hotkey',
            json={
                'keys': ['ctrl', 'c'],
                'intervalSeconds': 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['success'] is True
        assert data['data']['message'] == '完成'
        mock_desktop_service.hotkey.assert_called_once()
