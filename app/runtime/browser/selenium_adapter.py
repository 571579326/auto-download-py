import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SeleniumAdapter:

    def create_selenium_driver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
        except ImportError as exc:
            raise RuntimeError('缺少 selenium 依赖，请先执行: uv add selenium') from exc

        options = Options()
        options.debugger_address = f'127.0.0.1:{settings.debug_port}'
        if settings.browser_executable_path:
            options.binary_location = settings.browser_executable_path

        chromedriver_path = (settings.selenium_chromedriver_path or '').strip()
        if chromedriver_path:
            service = Service(chromedriver_path)
            return webdriver.Chrome(service=service, options=options)
        return webdriver.Chrome(options=options)


selenium_adapter = SeleniumAdapter()
