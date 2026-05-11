import logging
from urllib.parse import quote

from app.core.config import get_settings
from app.utils.http_utils import get_json, put_json

logger = logging.getLogger(__name__)
settings = get_settings()


class CdpClient:

    def build_cdp_url(self) -> str:
        return f'http://127.0.0.1:{settings.debug_port}'

    def is_cdp_http_open_page_mode(self) -> bool:
        return (settings.open_page_mode or '').strip().lower() in {'cdp_http', 'cdp-http', 'cdphttp', 'http'}

    def is_native_open_page_mode(self) -> bool:
        return (settings.open_page_mode or '').strip().lower() == 'native'

    def open_url_by_cdp_http(self, url: str) -> dict:
        safe_url = url or 'about:blank'
        encoded_url = quote(safe_url, safe='')
        endpoint = f'{self.build_cdp_url()}/json/new?{encoded_url}'
        timeout = max(settings.cdp_http_open_timeout_ms / 1000, 1)
        try:
            payload = put_json(endpoint, timeout=timeout)
        except Exception as exc:
            logger.warning('CDP HTTP PUT /json/new 失败，尝试 GET 回退, url=%s, msg=%s', safe_url, exc)
            payload = get_json(endpoint, timeout=timeout)
        if not isinstance(payload, dict):
            raise RuntimeError(f'CDP HTTP打开页面返回值异常: type={type(payload).__name__}, payload={payload}')
        logger.info(
            'CDP HTTP打开页面请求成功, targetId=%s, url=%s',
            payload.get('id') or payload.get('targetId'),
            payload.get('url') or safe_url,
        )
        return payload

    def log_cdp_diagnostics(self, runtime) -> None:
        try:
            version = runtime.browser_cdp.send('Browser.getVersion')
            logger.info(
                'Chrome diagnostics, product=%s, userAgent=%s, profileDir=%s, debugPort=%s, pageCount=%s',
                version.get('product'),
                version.get('userAgent'),
                settings.profile_dir,
                settings.debug_port,
                len(runtime.context.pages),
            )
        except Exception as exc:
            logger.warning('Chrome version diagnostics failed, msg=%s', exc)

        try:
            targets = get_json(f'http://127.0.0.1:{settings.debug_port}/json/list', timeout=2)
            if not isinstance(targets, list):
                logger.warning('CDP target diagnostics returned non-list payload, type=%s', type(targets).__name__)
                return

            extension_pages = [
                target
                for target in targets
                if str(target.get('url', '')).startswith('chrome-extension://')
                and target.get('type') == 'page'
            ]
            extension_workers = [
                target
                for target in targets
                if str(target.get('url', '')).startswith('chrome-extension://')
                and target.get('type') in {'service_worker', 'background_page'}
            ]
            logger.info(
                'Chrome extension diagnostics, targetCount=%s, extensionPages=%s, extensionWorkers=%s',
                len(targets),
                len(extension_pages),
                len(extension_workers),
            )
        except Exception as exc:
            logger.warning('CDP target diagnostics failed, msg=%s', exc)


cdp_client = CdpClient()
