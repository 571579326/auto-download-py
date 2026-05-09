import logging

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.browser import router as browser_router
from app.api.business import router as business_router
from app.api.health import router as health_router
from app.api.rpa import router as rpa_router
from app.api.desktop import router as desktop_router
from app.browser.manager import browser_session_manager
from app.core.asyncio_policy import ensure_windows_proactor_event_loop_policy
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401


setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

# Windows 下提前切到支持 subprocess 的 event loop policy
ensure_windows_proactor_event_loop_policy()

app = FastAPI(title=settings.app_name)
app.include_router(browser_router, prefix=settings.app_context_path)
app.include_router(business_router, prefix=settings.app_context_path)
app.include_router(health_router, prefix=settings.app_context_path)
app.include_router(desktop_router, prefix=settings.app_context_path)
app.include_router(rpa_router, prefix=settings.app_context_path)


@app.on_event('startup')
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info(
        'auto-download-py 启动完成，contextPath=%s, debugPort=%s, eventLoopPolicy=%s',
        settings.app_context_path,
        settings.debug_port,
        asyncio.get_event_loop_policy().__class__.__name__,
    )


@app.on_event('shutdown')
def on_shutdown() -> None:
    logger.info('auto-download-py 正在关闭，准备释放运行时浏览器连接')
    browser_session_manager.shutdown()


@app.exception_handler(ValueError)
async def handle_value_error(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={'code': 400, 'message': str(exc), 'data': None})


@app.exception_handler(RuntimeError)
async def handle_runtime_error(_: Request, exc: RuntimeError):
    logger.exception('RuntimeError: %s', exc)
    message = str(exc).strip()
    if not message:
        message = f'RuntimeError({exc.__class__.__name__})，请查看服务日志'
    return JSONResponse(status_code=500, content={'code': 500, 'message': message, 'data': None})


@app.exception_handler(Exception)
async def handle_exception(_: Request, exc: Exception):
    logger.exception('未处理异常: %s', exc)
    message = str(exc).strip()
    if not message:
        message = f'系统异常: {exc.__class__.__name__}，请查看服务日志'
    else:
        message = f'系统异常: {message}'
    return JSONResponse(status_code=500, content={'code': 500, 'message': message, 'data': None})
