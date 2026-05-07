import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


def ensure_windows_proactor_event_loop_policy() -> None:
    """
    Windows 下强制切到 ProactorEventLoopPolicy。
    Playwright Sync API 在启动 driver 子进程时依赖 asyncio.create_subprocess_exec，
    如果当前 policy 是 Selector，会在 Windows 上抛 NotImplementedError。
    """
    if sys.platform != "win32":
        return

    policy_cls = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    if policy_cls is None:
        return

    current_policy = asyncio.get_event_loop_policy()
    if isinstance(current_policy, policy_cls):
        logger.info(
            "当前 asyncio event loop policy 已是 %s",
            current_policy.__class__.__name__,
        )
        return

    asyncio.set_event_loop_policy(policy_cls())
    logger.info(
        "已切换 asyncio event loop policy -> %s",
        asyncio.get_event_loop_policy().__class__.__name__,
    )