import logging
import os
import subprocess
import time
from typing import Optional

from app.core.config import get_settings
from app.utils.http_utils import get_json
from app.utils.port_utils import is_port_open

logger = logging.getLogger(__name__)
settings = get_settings()


class BrowserProcessLauncher:

    def ensure_profile_dir(self) -> None:
        os.makedirs(settings.profile_dir, exist_ok=True)

    def ensure_browser_executable_path(self) -> None:
        if not os.path.isfile(settings.browser_executable_path):
            raise FileNotFoundError(f'浏览器可执行文件不存在: {settings.browser_executable_path}')

    def launch_browser_process(self) -> subprocess.Popen:
        start_url = settings.start_url or 'about:blank'
        command = self._build_browser_process_command(start_url)
        logger.info(
            'starting Chrome process, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_process(command)

    def launch_browser_new_window_process(self, url: str) -> subprocess.Popen:
        command = self._build_browser_process_command(url or 'about:blank')
        logger.info(
            'starting native Chrome new window, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_process(command)

    def launch_browser_pure_process(self, url: str, new_window: bool) -> subprocess.Popen:
        command = self._build_browser_pure_command(url, new_window)
        logger.info(
            'starting Chrome process by pure mode, command=%s, profileDir=%s, debugPort=%s',
            command,
            settings.profile_dir,
            settings.debug_port,
        )
        return self._popen_browser_pure_process(command)

    def wait_for_cdp_ready(self, browser_process: subprocess.Popen) -> None:
        deadline = time.time() + settings.cdp_ready_max_wait_ms / 1000
        version_url = f'http://127.0.0.1:{settings.debug_port}/json/version'
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            return_code = browser_process.poll()
            if return_code is not None:
                stderr_text = ''
                stdout_text = ''
                try:
                    if browser_process.stderr is not None:
                        stderr_text = browser_process.stderr.read()
                except Exception:
                    pass
                try:
                    if browser_process.stdout is not None:
                        stdout_text = browser_process.stdout.read()
                except Exception:
                    pass
                raise RuntimeError(
                    '浏览器进程已提前退出, '
                    f'returnCode={return_code}, stderr={stderr_text.strip() or "<empty>"}, stdout={stdout_text.strip() or "<empty>"}'
                )
            try:
                if is_port_open('127.0.0.1', settings.debug_port):
                    payload = get_json(version_url, timeout=2)
                    websocket_url = payload.get('webSocketDebuggerUrl')
                    logger.info('CDP探测成功, versionUrl=%s, websocket=%s', version_url, websocket_url)
                    if websocket_url:
                        return
            except Exception as exc:
                last_error = exc
            time.sleep(settings.cdp_ready_retry_interval_ms / 1000)
        raise RuntimeError(f'等待CDP就绪超时: {last_error}')

    def _build_browser_pure_command(self, url: str, new_window: bool) -> list[str]:
        command = [
            settings.browser_executable_path,
            f'--remote-debugging-port={settings.debug_port}',
            f'--user-data-dir={settings.profile_dir}',
        ]
        if new_window:
            command.append('--new-window')
        safe_url = (url or '').strip()
        if safe_url:
            command.append(safe_url)
        return command

    def _build_browser_process_command(self, url: str) -> list[str]:
        command = [
            settings.browser_executable_path,
            f'--remote-debugging-port={settings.debug_port}',
            f'--user-data-dir={settings.profile_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--new-window',
        ]
        if settings.headless:
            command.append('--headless=new')
        if url:
            command.append(url)
        return command

    def _popen_browser_pure_process(self, command: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )

    def _popen_browser_process(self, command: list[str]) -> subprocess.Popen:
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )


browser_process_launcher = BrowserProcessLauncher()
