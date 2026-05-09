import socket
from unittest.mock import MagicMock, patch

import pytest

from app.utils.image_utils import (
    click_image_if_exists,
    click_images_until_found,
    normalize_image_paths,
    normalize_match_mode,
)
from app.utils.port_utils import is_port_open
from app.utils.http_utils import get_json, put_json


class TestNormalizeMatchMode:
    def test_or_variants(self):
        assert normalize_match_mode("or") == "or"
        assert normalize_match_mode("any") == "or"
        assert normalize_match_mode("或") == "or"

    def test_and_variants(self):
        assert normalize_match_mode("and") == "and"
        assert normalize_match_mode("all") == "and"
        assert normalize_match_mode("和") == "and"

    def test_none_defaults_to_or(self):
        assert normalize_match_mode(None) == "or"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="matchMode"):
            normalize_match_mode("xor")

    def test_case_insensitive(self):
        assert normalize_match_mode("OR") == "or"
        assert normalize_match_mode("AND") == "and"

    def test_whitespace_stripped(self):
        assert normalize_match_mode("  or  ") == "or"


class TestNormalizeImagePaths:
    def test_list_of_paths(self):
        result = normalize_image_paths(["a.png", "b.png"])
        assert result == ["a.png", "b.png"]

    def test_deduplication(self):
        result = normalize_image_paths(["a.png", "a.png", "b.png"])
        assert result == ["a.png", "b.png"]

    def test_empty_string_filtered(self):
        result = normalize_image_paths(["a.png", "", "  ", "b.png"])
        assert result == ["a.png", "b.png"]

    def test_none_handling(self):
        result = normalize_image_paths(None, None)
        assert result == []

    def test_single_image_path(self):
        result = normalize_image_paths(None, "a.png")
        assert result == ["a.png"]

    def test_combined_paths(self):
        result = normalize_image_paths(["a.png"], "b.png")
        assert result == ["a.png", "b.png"]

    def test_whitespace_stripped(self):
        result = normalize_image_paths(["  a.png  "])
        assert result == ["a.png"]


class TestClickImageIfExists:
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_success_returns_true(self, mock_click):
        from app.schemas.desktop import ClickImageResponse

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=500, centerY=300,
            left=480, top=280, width=40, height=40,
            imagePath="test.png", confidence=0.9,
        )
        result = click_image_if_exists("test.png")
        assert result is True

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_failure_returns_false(self, mock_click):
        mock_click.side_effect = RuntimeError("图像未找到")
        result = click_image_if_exists("test.png")
        assert result is False

    def test_none_image_path_returns_false(self):
        result = click_image_if_exists(None)
        assert result is False

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_error_handler_called(self, mock_click):
        mock_click.side_effect = RuntimeError("图像检测失败")
        handler_calls = []

        def handler(exc):
            handler_calls.append(str(exc))

        result = click_image_if_exists("test.png", error_handler=handler)
        assert result is False
        assert len(handler_calls) == 1
        assert "图像检测失败" in handler_calls[0]

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_error_handler_exception_handled(self, mock_click):
        mock_click.side_effect = RuntimeError("fail")

        def bad_handler(exc):
            raise RuntimeError("handler error")

        result = click_image_if_exists("test.png", error_handler=bad_handler)
        assert result is False

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_custom_params_passed(self, mock_click):
        from app.schemas.desktop import ClickImageResponse

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=100, centerY=200,
            left=90, top=190, width=20, height=20,
            imagePath="test.png", confidence=0.85,
        )
        click_image_if_exists("test.png", confidence=0.85, timeout_ms=3000, retry_interval_ms=200)
        call_arg = mock_click.call_args[0][0]
        assert call_arg.confidence == 0.85
        assert call_arg.timeoutMs == 3000
        assert call_arg.retryIntervalMs == 200


class TestClickImagesUntilFound:
    @patch("app.utils.image_utils.visual_service.click_image")
    def test_or_mode_success(self, mock_click):
        from app.schemas.desktop import ClickImageResponse

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=500, centerY=300,
            left=480, top=280, width=40, height=40,
            imagePath="a.png", confidence=0.9,
        )
        result = click_images_until_found(
            image_paths=["a.png", "b.png"],
            confidence=0.9,
            timeout_ms=5000,
            retry_interval_ms=500,
            match_mode="or",
        )
        assert len(result) == 1
        assert result[0].clicked is True

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_or_mode_timeout_raises(self, mock_click):
        mock_click.side_effect = RuntimeError("not found")
        with pytest.raises(RuntimeError, match="OR模式"):
            click_images_until_found(
                image_paths=["a.png"],
                confidence=0.9,
                timeout_ms=500,
                retry_interval_ms=200,
                match_mode="or",
            )

    @patch("app.utils.image_utils.visual_service.click_image")
    def test_and_mode_success(self, mock_click):
        from app.schemas.desktop import ClickImageResponse

        mock_click.return_value = ClickImageResponse(
            clicked=True, centerX=500, centerY=300,
            left=480, top=280, width=40, height=40,
            imagePath="a.png", confidence=0.9,
        )
        result = click_images_until_found(
            image_paths=["a.png", "b.png"],
            confidence=0.9,
            timeout_ms=5000,
            retry_interval_ms=500,
            match_mode="and",
        )
        assert len(result) == 2

    def test_empty_paths_raises(self):
        with pytest.raises(ValueError, match="imagePaths不能为空"):
            click_images_until_found(
                image_paths=[],
                confidence=0.9,
                timeout_ms=5000,
                retry_interval_ms=500,
            )


class TestIsPortOpen:
    @patch("socket.socket")
    def test_open_port(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert is_port_open("127.0.0.1", 8080) is True

    @patch("socket.socket")
    def test_closed_port(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1
        mock_socket_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
        mock_socket_cls.return_value.__exit__ = MagicMock(return_value=False)
        assert is_port_open("127.0.0.1", 8080) is False


class TestGetJson:
    @patch("app.utils.http_utils.requests.get")
    def test_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        result = get_json("http://example.com/api", timeout=5)
        assert result == {"key": "value"}

    @patch("app.utils.http_utils.requests.get")
    def test_http_error_raises(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        with pytest.raises(Exception, match="Connection error"):
            get_json("http://example.com/api", timeout=5)


class TestPutJson:
    @patch("app.utils.http_utils.requests.put")
    def test_success(self, mock_put):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status.return_value = None
        mock_put.return_value = mock_response
        result = put_json("http://example.com/api", timeout=5)
        assert result == {"status": "ok"}

    @patch("app.utils.http_utils.requests.put")
    def test_http_error_raises(self, mock_put):
        mock_put.side_effect = Exception("Connection error")
        with pytest.raises(Exception, match="Connection error"):
            put_json("http://example.com/api", timeout=5)
