from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.schemas.browser import (
    BatchOpenPagesResponse,
    BingHuyaRequest,
    ClosePageResponse,
    InvalidateWindowResponse,
    NewTabRequest,
    OpenConfiguredPagesRequest,
    OpenUrlRequest,
    OpenWindowResponse,
    PageInfoResponse,
    PageListResponse,
    PageSummary,
    ReopenWindowResponse,
    SeleniumOpenWindowResponse,
    WindowListResponse,
    WindowSummary,
)

client = TestClient(app)

BASE_URL = '/auto-download/browser'


def _mock_open_window_response():
    return OpenWindowResponse(
        windowId='w-001',
        sessionId='w-001',
        status='1',
        userDataDir='/tmp/profile',
        debugPort=9222,
    )


def _mock_selenium_open_window_response():
    return SeleniumOpenWindowResponse(
        windowId='w-001',
        sessionId='w-001',
        status='1',
        userDataDir='/tmp/profile',
        debugPort=9222,
        url='https://example.com',
        title='Test',
        newWindow=True,
        browserStartedNow=False,
        driverDetached=True,
    )


def _mock_window_list_response():
    return WindowListResponse(
        total=1,
        windows=[WindowSummary(windowId='w-001', status='1')],
    )


def _mock_page_info_response():
    return PageInfoResponse(
        windowId='w-001',
        sessionId='w-001',
        pageId='p-001',
        pageIndex=1,
        title='Test',
        url='https://example.com',
        status='1',
    )


def _mock_page_list_response():
    return PageListResponse(
        windowId='w-001',
        sessionId='w-001',
        total=1,
        activePageId='p-001',
        activePageIndex=1,
        pages=[
            PageSummary(
                pageId='p-001',
                pageIndex=1,
                title='Test',
                url='https://example.com',
                status='1',
                isActive=True,
            )
        ],
    )


def _mock_batch_open_pages_response():
    return BatchOpenPagesResponse(
        windowId='w-001',
        sessionId='w-001',
        configCode='test',
        total=1,
        openedPages=[_mock_page_info_response()],
    )


def _mock_close_page_response():
    return ClosePageResponse(
        windowId='w-001',
        sessionId='w-001',
        pageId='p-001',
        closed=True,
        remainingPages=0,
    )


def _mock_invalidate_window_response():
    return InvalidateWindowResponse(
        windowId='w-001',
        sessionId='w-001',
        status='invalid',
        closed=True,
    )


def _mock_reopen_window_response():
    return ReopenWindowResponse(
        oldWindowId='w-001',
        newWindowId='w-002',
        status='1',
        restoredPages=1,
        closedOldWindow=True,
    )


class TestOpenWindow:

    @patch('app.api.browser.browser_service')
    def test_open_window_success(self, mock_svc):
        mock_svc.open_browser.return_value = _mock_open_window_response()
        response = client.post(f'{BASE_URL}/session/open')
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['windowId'] == 'w-001'
        mock_svc.open_browser.assert_called_once()


class TestOpenWindowPure:

    @patch('app.api.browser.browser_service')
    def test_open_window_pure_success(self, mock_svc):
        mock_svc.open_browser_pure.return_value = _mock_open_window_response()
        response = client.post(
            f'{BASE_URL}/session/open-pure',
            params={'url': 'https://example.com', 'newWindow': True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['windowId'] == 'w-001'
        mock_svc.open_browser_pure.assert_called_once_with('https://example.com', True)


class TestOpenWindowSelenium:

    @patch('app.api.browser.browser_service')
    def test_open_window_selenium_success(self, mock_svc):
        mock_svc.open_browser_selenium.return_value = _mock_selenium_open_window_response()
        response = client.post(
            f'{BASE_URL}/session/open-selenium',
            params={'url': 'https://example.com', 'newWindow': True, 'ensureBrowser': False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['windowId'] == 'w-001'
        mock_svc.open_browser_selenium.assert_called_once_with('https://example.com', True, False)


class TestListWindows:

    @patch('app.api.browser.browser_service')
    def test_list_windows_success(self, mock_svc):
        mock_svc.list_windows.return_value = _mock_window_list_response()
        response = client.get(f'{BASE_URL}/windows')
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['total'] == 1
        mock_svc.list_windows.assert_called_once()


class TestOpenTab:

    @patch('app.api.browser.browser_service')
    def test_open_tab_success(self, mock_svc):
        mock_svc.new_tab.return_value = _mock_page_info_response()
        response = client.post(
            f'{BASE_URL}/tab/open',
            params={'windowId': 'w-001'},
            json={'url': 'https://example.com', 'bringToFront': True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.new_tab.assert_called_once()
        call_args = mock_svc.new_tab.call_args
        assert call_args[0][0] == 'w-001'


class TestOpenUrl:

    @patch('app.api.browser.browser_service')
    def test_open_url_success(self, mock_svc):
        mock_svc.open_url.return_value = _mock_page_info_response()
        response = client.post(
            f'{BASE_URL}/page/open-url',
            params={'windowId': 'w-001'},
            json={'url': 'https://example.com', 'newTab': False, 'bringToFront': True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.open_url.assert_called_once()
        call_args = mock_svc.open_url.call_args
        assert call_args[0][0] == 'w-001'


class TestBatchOpenConfig:

    @patch('app.api.browser.browser_service')
    def test_batch_open_config_success(self, mock_svc):
        mock_svc.open_config_pages.return_value = _mock_batch_open_pages_response()
        response = client.post(
            f'{BASE_URL}/page/batch-open-config',
            params={'windowId': 'w-001'},
            json={'configCode': 'test', 'bringToFront': True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['configCode'] == 'test'
        mock_svc.open_config_pages.assert_called_once()
        call_args = mock_svc.open_config_pages.call_args
        assert call_args[0][0] == 'w-001'


class TestListPages:

    @patch('app.api.browser.browser_service')
    def test_list_pages_success(self, mock_svc):
        mock_svc.list_pages.return_value = _mock_page_list_response()
        response = client.get(f'{BASE_URL}/pages', params={'windowId': 'w-001'})
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['total'] == 1
        mock_svc.list_pages.assert_called_once_with('w-001')


class TestGetPageInfo:

    @patch('app.api.browser.browser_service')
    def test_get_page_info_success(self, mock_svc):
        mock_svc.get_page_info.return_value = _mock_page_info_response()
        response = client.get(
            f'{BASE_URL}/page-info',
            params={'windowId': 'w-001', 'pageId': 'p-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.get_page_info.assert_called_once_with('w-001', 'p-001', None)


class TestActivatePage:

    @patch('app.api.browser.browser_service')
    def test_activate_page_success(self, mock_svc):
        mock_svc.activate_page.return_value = _mock_page_info_response()
        response = client.post(
            f'{BASE_URL}/page/activate',
            params={'windowId': 'w-001', 'pageId': 'p-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.activate_page.assert_called_once_with('w-001', 'p-001', None)


class TestClosePage:

    @patch('app.api.browser.browser_service')
    def test_close_page_success(self, mock_svc):
        mock_svc.close_page.return_value = _mock_close_page_response()
        response = client.post(
            f'{BASE_URL}/page/close',
            params={'windowId': 'w-001', 'pageId': 'p-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['closed'] is True
        mock_svc.close_page.assert_called_once_with('w-001', 'p-001', None)


class TestBingHuya:

    @patch('app.api.browser.browser_service')
    def test_bing_huya_success(self, mock_svc):
        mock_svc.bing_huya.return_value = _mock_page_info_response()
        response = client.post(
            f'{BASE_URL}/bing-huya',
            params={'windowId': 'w-001'},
            json={'keyword': '虎牙直播lpl', 'targetPrefix': 'https://www.huya.com'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.bing_huya.assert_called_once()
        call_args = mock_svc.bing_huya.call_args
        assert call_args[0][0] == 'w-001'


class TestTakeoverPageInfo:

    @patch('app.api.browser.browser_service')
    def test_takeover_page_info_success(self, mock_svc):
        mock_svc.takeover_page_info.return_value = _mock_page_info_response()
        response = client.get(
            f'{BASE_URL}/takeover/page-info',
            params={'windowId': 'w-001', 'pageId': 'p-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['pageId'] == 'p-001'
        mock_svc.takeover_page_info.assert_called_once_with('w-001', 'p-001', None)


class TestReopenWindow:

    @patch('app.api.browser.browser_service')
    def test_reopen_window_success(self, mock_svc):
        mock_svc.reopen_window.return_value = _mock_reopen_window_response()
        response = client.post(
            f'{BASE_URL}/window/reopen',
            params={'windowId': 'w-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['newWindowId'] == 'w-002'
        mock_svc.reopen_window.assert_called_once_with('w-001')


class TestInvalidateWindow:

    @patch('app.api.browser.browser_service')
    def test_invalidate_window_success(self, mock_svc):
        mock_svc.invalidate_window.return_value = _mock_invalidate_window_response()
        response = client.post(
            f'{BASE_URL}/window/invalidate',
            params={'windowId': 'w-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['status'] == 'invalid'
        mock_svc.invalidate_window.assert_called_once_with('w-001')


class TestCloseBrowser:

    @patch('app.api.browser.browser_service')
    def test_close_browser_success(self, mock_svc):
        mock_svc.close_browser.return_value = _mock_invalidate_window_response()
        response = client.post(
            f'{BASE_URL}/close',
            params={'windowId': 'w-001'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert data['data']['closed'] is True
        mock_svc.close_browser.assert_called_once_with('w-001')


class TestResolveWindowId:

    def test_both_window_id_and_session_id_empty_returns_400(self):
        response = client.get(f'{BASE_URL}/pages')
        assert response.status_code == 400
        data = response.json()
        assert data['code'] == 400

    def test_session_id_used_as_fallback(self):
        with patch('app.api.browser.browser_service') as mock_svc:
            mock_svc.list_pages.return_value = _mock_page_list_response()
            response = client.get(f'{BASE_URL}/pages', params={'sessionId': 'w-001'})
            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            mock_svc.list_pages.assert_called_once_with('w-001')
