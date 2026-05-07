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

    profile_dir: str = Field(default='C:/cache/chromeTest/auto-download/shared-profile', alias='PROFILE_DIR')
    browser_executable_path: str = Field(default='C:/software/chrome-win64/chrome.exe', alias='BROWSER_EXECUTABLE_PATH')
    debug_port: int = Field(default=29222, alias='DEBUG_PORT')
    only_one_active_session: bool = Field(default=True, alias='ONLY_ONE_ACTIVE_SESSION')
    start_url: str = Field(default='about:blank', alias='START_URL')
    start_timeout_ms: int = Field(default=15000, alias='START_TIMEOUT_MS')
    cdp_connect_timeout_ms: int = Field(default=15000, alias='CDP_CONNECT_TIMEOUT_MS')
    bing_url: str = Field(default='https://www.bing.com', alias='BING_URL')
    headless: bool = Field(default=False, alias='HEADLESS')
    slow_mo_ms: int = Field(default=300, alias='SLOW_MO_MS')
    cdp_ready_retry_interval_ms: int = Field(default=500, alias='CDP_READY_RETRY_INTERVAL_MS')
    cdp_ready_max_wait_ms: int = Field(default=15000, alias='CDP_READY_MAX_WAIT_MS')

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
