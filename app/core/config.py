from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='auto-download-py', alias='APP_NAME')
    app_host: str = Field(default='0.0.0.0', alias='APP_HOST')
    app_port: int = Field(default=7982, alias='APP_PORT')
    app_context_path: str = Field(default='/auto-download', alias='APP_CONTEXT_PATH')

    @property
    def context_path(self) -> str:
        return self.app_context_path

    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    log_file: str = Field(default='./logs/auto-download-py.log', alias='LOG_FILE')

    db_host: str = Field(default='127.0.0.1', alias='DB_HOST')
    db_port: int = Field(default=3306, alias='DB_PORT')
    db_name: str = Field(default='auto_download', alias='DB_NAME')
    db_user: str = Field(default='root', alias='DB_USER')
    db_password: str = Field(default='root', alias='DB_PASSWORD')
    db_pool_size: int = Field(default=5, alias='DB_POOL_SIZE')
    db_max_overflow: int = Field(default=10, alias='DB_MAX_OVERFLOW')

    profile_dir: str = Field(default='C:/chrome_debug_profile', alias='PROFILE_DIR')
    browser_executable_path: str = Field(default='C:/software/chrome-win64/chrome.exe', alias='BROWSER_EXECUTABLE_PATH')
    debug_port: int = Field(default=9222, alias='DEBUG_PORT')
    only_one_active_session: bool = Field(default=True, alias='ONLY_ONE_ACTIVE_SESSION')
    start_url: str = Field(default='about:blank', alias='START_URL')
    start_timeout_ms: int = Field(default=5000, alias='START_TIMEOUT_MS')
    cdp_connect_timeout_ms: int = Field(default=5000, alias='CDP_CONNECT_TIMEOUT_MS')
    bing_url: str = Field(default='https://www.bing.com', alias='BING_URL')
    headless: bool = Field(default=False, alias='HEADLESS')
    slow_mo_ms: int = Field(default=0, alias='SLOW_MO_MS')
    cdp_ready_retry_interval_ms: int = Field(default=500, alias='CDP_READY_RETRY_INTERVAL_MS')
    cdp_ready_max_wait_ms: int = Field(default=10000, alias='CDP_READY_MAX_WAIT_MS')
    open_page_mode: str = Field(default='cdp_http', alias='OPEN_PAGE_MODE')

    auto_click_security_check: bool = Field(default=True, alias='AUTO_CLICK_SECURITY_CHECK')
    auto_click_image_paths: str = Field(
        default='C:/code/py/auto-download-py/app/visual/templates/cf_check_dark.png;C:/code/py/auto-download-py/app/visual/templates/cf_check_white.png',
        alias='AUTO_CLICK_IMAGE_PATHS',
    )
    auto_click_image_match_mode: str = Field(default='or', alias='AUTO_CLICK_IMAGE_MATCH_MODE')
    auto_click_image_confidence: float = Field(default=0.7, alias='AUTO_CLICK_IMAGE_CONFIDENCE')
    auto_click_image_timeout_ms: int = Field(default=30000, alias='AUTO_CLICK_IMAGE_TIMEOUT_MS')
    auto_click_image_retry_interval_ms: int = Field(default=400, alias='AUTO_CLICK_IMAGE_RETRY_INTERVAL_MS')
    # 图像点击偏移：相对匹配到的图片区域左上角计算。两者都为空时点击匹配框中心点。
    auto_click_image_click_offset_x: int | None = Field(default=None, alias='AUTO_CLICK_IMAGE_CLICK_OFFSET_X')
    auto_click_image_click_offset_y: int | None = Field(default=None, alias='AUTO_CLICK_IMAGE_CLICK_OFFSET_Y')
    # 点击前激活目标窗口，避免图像识别到了但点击落不到 Chrome 窗口。
    auto_click_activate_window_before: bool = Field(default=True, alias='AUTO_CLICK_ACTIVATE_WINDOW_BEFORE')
    auto_click_window_title_regex: str = Field(default='.*(hxcy|Cloudflare|安全|驗證|验证|Chrome).*', alias='AUTO_CLICK_WINDOW_TITLE_REGEX')
    page_stabilize_seconds: float = Field(default=3.0, alias='PAGE_STABILIZE_SECONDS')
    cdp_http_open_timeout_ms: int = Field(default=5000, alias='CDP_HTTP_OPEN_TIMEOUT_MS')

    pure_browser_start_url: str = Field(default='', alias='PURE_BROWSER_START_URL')
    pure_browser_new_window: bool = Field(default=False, alias='PURE_BROWSER_NEW_WINDOW')

    selenium_browser_start_url: str = Field(default='about:blank', alias='SELENIUM_BROWSER_START_URL')
    selenium_browser_new_window: bool = Field(default=True, alias='SELENIUM_BROWSER_NEW_WINDOW')
    selenium_page_load_timeout_ms: int = Field(default=8000, alias='SELENIUM_PAGE_LOAD_TIMEOUT_MS')
    selenium_chromedriver_path: str = Field(default='', alias='SELENIUM_CHROMEDRIVER_PATH')
    selenium_read_page_info: bool = Field(default=False, alias='SELENIUM_READ_PAGE_INFO')

    playwright_once_new_window: bool = Field(default=True, alias='PLAYWRIGHT_ONCE_NEW_WINDOW')
    playwright_once_connect_timeout_ms: int = Field(default=5000, alias='PLAYWRIGHT_ONCE_CONNECT_TIMEOUT_MS')
    playwright_once_navigation_timeout_ms: int = Field(default=3000, alias='PLAYWRIGHT_ONCE_NAVIGATION_TIMEOUT_MS')
    playwright_once_read_page_info: bool = Field(default=False, alias='PLAYWRIGHT_ONCE_READ_PAGE_INFO')

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
