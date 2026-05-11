import threading
from dataclasses import dataclass, field

from playwright.sync_api import Browser, BrowserContext, CDPSession, Page, Playwright


@dataclass
class BrowserRuntime:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    browser_cdp: CDPSession
    lock: threading.RLock


@dataclass
class WindowRuntime:
    lock: threading.RLock = field(default_factory=threading.RLock)
    page_map: dict[int, Page] = field(default_factory=dict)
    active_page_db_id: int | None = None
    root_page_db_id: int | None = None
