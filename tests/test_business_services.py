from unittest.mock import MagicMock, patch

import pytest

from app.schemas.browser import BatchOpenPagesResponse, PageInfoResponse
from app.services.business_common_service import (
    BusinessCommonService,
    BusinessOpenMode,
    BusinessPageFlowContext,
    business_common_service,
)
from app.services.business_image_click_service import (
    BusinessImageClickOptions,
    BusinessImageClickResult,
    BusinessImageClickService,
    business_image_click_service,
    split_image_paths,
)
from app.services.business_service import BusinessService, business_service


class TestBusinessService:
    @patch('app.services.business_service.business_common_service')
    def test_open_pages_and_check_image_delegates_playwright_once(self, mock_common):
        mock_context = BusinessPageFlowContext(
            config_code='test_code',
            open_mode='playwright_once',
            image_click_options=BusinessImageClickOptions(enabled=True),
        )
        mock_pages_response = BatchOpenPagesResponse(
            windowId='w-001',
            sessionId='s-001',
            configCode='test_code',
            total=1,
            openedPages=[
                PageInfoResponse(
                    windowId='w-001',
                    sessionId='s-001',
                    pageId='p-1',
                    pageIndex=1,
                    title='Test',
                    url='https://example.com',
                    status='1',
                )
            ],
        )
        mock_image_result = BusinessImageClickResult(
            clicked=True,
            skipped=False,
            image_paths=['img.png'],
            match_mode='or',
            clicked_images=[{'imagePath': 'img.png'}],
        )
        mock_common.build_page_flow_context.return_value = mock_context
        mock_common.open_config_pages_by_mode.return_value = mock_pages_response
        mock_common.wait_page_stable.return_value = None
        mock_common.find_and_click_images_for_flow.return_value = mock_image_result
        mock_common.build_page_flow_result.return_value = {
            'windowId': 'w-001',
            'pagesOpened': 1,
            'imageClicked': True,
        }

        result = business_service.open_pages_and_check_image(config_code='test_code')

        mock_common.build_page_flow_context.assert_called_once_with(
            config_code='test_code',
            open_mode='playwright_once',
            click_offset_x=None,
            click_offset_y=None,
        )
        mock_common.open_config_pages_by_mode.assert_called_once_with(mock_context)
        mock_common.wait_page_stable.assert_called_once_with(page_count=1)
        mock_common.find_and_click_images_for_flow.assert_called_once_with(mock_context)
        mock_common.build_page_flow_result.assert_called_once_with(
            context=mock_context,
            pages_response=mock_pages_response,
            image_click_result=mock_image_result,
        )
        assert result == {'windowId': 'w-001', 'pagesOpened': 1, 'imageClicked': True}

    @patch('app.services.business_service.business_common_service')
    def test_open_pages_and_check_image_selenium_delegates_selenium_once(self, mock_common):
        mock_context = BusinessPageFlowContext(
            config_code='test_code',
            open_mode='selenium_once',
            image_click_options=BusinessImageClickOptions(enabled=True),
        )
        mock_pages_response = BatchOpenPagesResponse(
            windowId='w-002',
            sessionId='s-002',
            configCode='test_code',
            total=2,
            openedPages=[
                PageInfoResponse(
                    windowId='w-002',
                    sessionId='s-002',
                    pageId='p-2',
                    pageIndex=1,
                    title='Test',
                    url='https://example.com',
                    status='1',
                )
            ],
        )
        mock_image_result = BusinessImageClickResult(
            clicked=False,
            skipped=False,
            image_paths=[],
            match_mode='or',
        )
        mock_common.build_page_flow_context.return_value = mock_context
        mock_common.open_config_pages_by_mode.return_value = mock_pages_response
        mock_common.wait_page_stable.return_value = None
        mock_common.find_and_click_images_for_flow.return_value = mock_image_result
        mock_common.build_page_flow_result.return_value = {
            'windowId': 'w-002',
            'pagesOpened': 2,
            'imageClicked': False,
        }

        result = business_service.open_pages_and_check_image_selenium(
            config_code='test_code',
            click_offset_x=10,
            click_offset_y=20,
        )

        mock_common.build_page_flow_context.assert_called_once_with(
            config_code='test_code',
            open_mode='selenium_once',
            click_offset_x=10,
            click_offset_y=20,
        )
        assert result == {'windowId': 'w-002', 'pagesOpened': 2, 'imageClicked': False}

    @patch('app.services.business_service.business_common_service')
    def test_open_pages_and_check_image_propagates_exception(self, mock_common):
        mock_context = BusinessPageFlowContext(
            config_code='bad_code',
            open_mode='playwright_once',
            image_click_options=BusinessImageClickOptions(enabled=True),
        )
        mock_common.build_page_flow_context.return_value = mock_context
        mock_common.open_config_pages_by_mode.side_effect = ValueError('no valid page config')

        with pytest.raises(ValueError, match='no valid page config'):
            business_service.open_pages_and_check_image(config_code='bad_code')


class TestBusinessCommonService:
    def test_validate_open_mode_with_valid_playwright_once(self):
        BusinessCommonService.validate_open_mode('playwright_once')

    def test_validate_open_mode_with_valid_selenium_once(self):
        BusinessCommonService.validate_open_mode('selenium_once')

    def test_validate_open_mode_with_invalid_mode_raises(self):
        with pytest.raises(ValueError, match='不支持的业务打开模式'):
            BusinessCommonService.validate_open_mode('invalid_mode')

    @patch('app.services.business_common_service.time.sleep')
    @patch('app.services.business_common_service.settings')
    def test_wait_page_stable_with_page_count_and_seconds(self, mock_settings, mock_sleep):
        mock_settings.page_stabilize_seconds = 3.0

        BusinessCommonService.wait_page_stable(page_count=2)

        mock_sleep.assert_called_once_with(3.0)

    @patch('app.services.business_common_service.time.sleep')
    @patch('app.services.business_common_service.settings')
    def test_wait_page_stable_with_page_count_zero_does_not_sleep(self, mock_settings, mock_sleep):
        mock_settings.page_stabilize_seconds = 3.0

        BusinessCommonService.wait_page_stable(page_count=0)

        mock_sleep.assert_not_called()

    @patch('app.services.business_common_service.time.sleep')
    @patch('app.services.business_common_service.settings')
    def test_wait_page_stable_with_seconds_zero_does_not_sleep(self, mock_settings, mock_sleep):
        mock_settings.page_stabilize_seconds = 3.0

        BusinessCommonService.wait_page_stable(page_count=1, seconds=0)

        mock_sleep.assert_not_called()

    def test_build_page_flow_result_returns_correct_structure(self):
        mock_context = BusinessPageFlowContext(
            config_code='cfg1',
            open_mode='playwright_once',
            image_click_options=BusinessImageClickOptions(
                enabled=True,
                click_offset_x=5,
                click_offset_y=10,
            ),
        )
        mock_pages_response = BatchOpenPagesResponse(
            windowId='w-001',
            sessionId='s-001',
            configCode='cfg1',
            total=2,
            openedPages=[
                PageInfoResponse(
                    windowId='w-001',
                    sessionId='s-001',
                    pageId='p-1',
                    pageIndex=1,
                    title='Page1',
                    url='https://a.com',
                    status='1',
                )
            ],
        )
        mock_image_result = BusinessImageClickResult(
            clicked=True,
            skipped=False,
            image_paths=['img1.png', 'img2.png'],
            match_mode='or',
            clicked_images=[{'imagePath': 'img1.png'}],
            click_offset_x=5,
            click_offset_y=10,
        )

        result = BusinessCommonService.build_page_flow_result(
            context=mock_context,
            pages_response=mock_pages_response,
            image_click_result=mock_image_result,
        )

        assert result['windowId'] == 'w-001'
        assert result['pagesOpened'] == 2
        assert len(result['openedPages']) == 1
        assert result['imageClicked'] is True
        assert result['clickedImages'] == [{'imagePath': 'img1.png'}]
        assert result['imagePaths'] == ['img1.png', 'img2.png']
        assert result['imageMatchMode'] == 'or'
        assert result['imageClickOffsetX'] == 5
        assert result['imageClickOffsetY'] == 10
        assert result['imageClickOffsetBase'] == 'matched_image_top_left'
        assert result['imageError'] is None
        assert result['imageClickSkipped'] is False
        assert result['imageClickSkipReason'] is None
        assert result['configCode'] == 'cfg1'
        assert result['openMode'] == 'playwright_once'
        assert result['attachMode'] == 'short'
        assert result['driverDetached'] is True

    @patch('app.services.business_common_service.business_image_click_service')
    def test_build_page_flow_context_creates_context_with_correct_fields(self, mock_image_click_svc):
        mock_options = BusinessImageClickOptions(
            enabled=True,
            image_paths=['img.png'],
            match_mode='or',
            confidence=0.9,
            click_offset_x=5,
            click_offset_y=10,
        )
        mock_image_click_svc.build_auto_click_options.return_value = mock_options

        context = business_common_service.build_page_flow_context(
            config_code='cfg1',
            open_mode='playwright_once',
            click_offset_x=5,
            click_offset_y=10,
        )

        assert context.config_code == 'cfg1'
        assert context.open_mode == 'playwright_once'
        assert context.image_click_options is mock_options
        mock_image_click_svc.build_auto_click_options.assert_called_once_with(
            click_offset_x=5,
            click_offset_y=10,
        )


class TestBusinessImageClickService:
    def test_resolve_click_offset_with_both_offsets(self):
        result = business_image_click_service.resolve_click_offset(
            click_offset_x=10,
            click_offset_y=20,
        )

        assert result == (10, 20)

    def test_resolve_click_offset_with_only_x_raises(self):
        with pytest.raises(ValueError, match='clickOffsetX/clickOffsetY 需要同时传入'):
            business_image_click_service.resolve_click_offset(click_offset_x=10, click_offset_y=None)

    def test_resolve_click_offset_with_only_y_raises(self):
        with pytest.raises(ValueError, match='clickOffsetX/clickOffsetY 需要同时传入'):
            business_image_click_service.resolve_click_offset(click_offset_x=None, click_offset_y=20)

    @patch('app.services.business_image_click_service.settings')
    def test_resolve_click_offset_with_no_offsets_returns_none(self, mock_settings):
        mock_settings.auto_click_image_click_offset_x = None
        mock_settings.auto_click_image_click_offset_y = None

        result = business_image_click_service.resolve_click_offset(
            click_offset_x=None,
            click_offset_y=None,
        )

        assert result == (None, None)

    @patch('app.services.business_image_click_service.settings')
    def test_resolve_click_offset_falls_back_to_config(self, mock_settings):
        mock_settings.auto_click_image_click_offset_x = 30
        mock_settings.auto_click_image_click_offset_y = 40

        result = business_image_click_service.resolve_click_offset(
            click_offset_x=None,
            click_offset_y=None,
        )

        assert result == (30, 40)

    def test_find_and_click_images_when_disabled_returns_skipped(self):
        options = BusinessImageClickOptions(
            enabled=False,
            image_paths=['img.png'],
        )

        result = business_image_click_service.find_and_click_images(options=options)

        assert result.clicked is False
        assert result.skipped is True
        assert result.skip_reason == 'auto_click_disabled'

    def test_find_and_click_images_with_empty_paths_returns_skipped(self):
        options = BusinessImageClickOptions(
            enabled=True,
            image_paths=[],
        )

        result = business_image_click_service.find_and_click_images(options=options)

        assert result.clicked is False
        assert result.skipped is True
        assert result.skip_reason == 'image_paths_empty'

    @patch('app.services.business_image_click_service.click_images_until_found')
    def test_find_and_click_images_success(self, mock_click_until_found):
        from app.schemas.desktop import ClickImageResponse

        mock_click_response = ClickImageResponse(
            clicked=True,
            centerX=500,
            centerY=300,
            left=480,
            top=280,
            width=40,
            height=40,
            imagePath='img.png',
            confidence=0.9,
        )
        mock_click_until_found.return_value = [mock_click_response]

        options = BusinessImageClickOptions(
            enabled=True,
            image_paths=['img.png'],
            match_mode='or',
            confidence=0.9,
            timeout_ms=10000,
            retry_interval_ms=400,
        )

        result = business_image_click_service.find_and_click_images(options=options, scene='test')

        assert result.clicked is True
        assert result.skipped is False
        assert len(result.clicked_images) == 1
        assert result.clicked_images[0]['imagePath'] == 'img.png'

    @patch('app.services.business_image_click_service.click_images_until_found')
    def test_find_and_click_images_failure_returns_clicked_false_with_error(self, mock_click_until_found):
        mock_click_until_found.side_effect = RuntimeError('超时未找到目标图片')

        options = BusinessImageClickOptions(
            enabled=True,
            image_paths=['img.png'],
            match_mode='or',
            confidence=0.9,
            timeout_ms=10000,
            retry_interval_ms=400,
        )

        result = business_image_click_service.find_and_click_images(options=options, scene='test')

        assert result.clicked is False
        assert result.skipped is False
        assert result.error == '超时未找到目标图片'

    @patch('app.services.business_image_click_service.settings')
    def test_build_auto_click_options_reads_from_settings(self, mock_settings):
        mock_settings.auto_click_security_check = True
        mock_settings.auto_click_image_paths = 'a.png;b.png'
        mock_settings.auto_click_image_match_mode = 'or'
        mock_settings.auto_click_image_confidence = 0.8
        mock_settings.auto_click_image_timeout_ms = 5000
        mock_settings.auto_click_image_retry_interval_ms = 300
        mock_settings.auto_click_image_click_offset_x = None
        mock_settings.auto_click_image_click_offset_y = None

        result = business_image_click_service.build_auto_click_options()

        assert result.enabled is True
        assert result.image_paths == ['a.png', 'b.png']
        assert result.match_mode == 'or'
        assert result.confidence == 0.8
        assert result.timeout_ms == 5000
        assert result.retry_interval_ms == 300
        assert result.click_offset_x is None
        assert result.click_offset_y is None


class TestSplitImagePaths:
    def test_empty_string_returns_empty_list(self):
        assert split_image_paths('') == []

    def test_none_returns_empty_list(self):
        assert split_image_paths(None) == []

    def test_single_path_returns_list_with_path(self):
        assert split_image_paths('C:/a.png') == ['C:/a.png']

    def test_multiple_semicolon_separated_paths(self):
        result = split_image_paths('C:/a.png;C:/b.png;C:/c.png')
        assert result == ['C:/a.png', 'C:/b.png', 'C:/c.png']

    def test_whitespace_handling(self):
        result = split_image_paths('  C:/a.png  ;  C:/b.png  ')
        assert result == ['C:/a.png', 'C:/b.png']

    def test_empty_items_are_filtered(self):
        result = split_image_paths('C:/a.png;;C:/b.png;')
        assert result == ['C:/a.png', 'C:/b.png']

    def test_whitespace_only_items_are_filtered(self):
        result = split_image_paths('C:/a.png;   ;C:/b.png')
        assert result == ['C:/a.png', 'C:/b.png']
