"""本地业务代码直接调用示例。"""

from app.schemas.browser import NewTabRequest, OpenUrlRequest
from app.services.browser_service import browser_service


def main() -> None:
    opened = browser_service.open_browser()
    window_id = opened.windowId
    print('open_browser ->', opened.model_dump())

    page = browser_service.new_tab(window_id, NewTabRequest(url='https://www.bing.com'))
    print('new_tab ->', page.model_dump())

    pages = browser_service.list_pages(window_id)
    print('list_pages ->', pages.model_dump())

    page = browser_service.open_url(
        window_id,
        OpenUrlRequest(url='https://www.example.com', pageId=page.pageId, newTab=False),
    )
    print('open_url ->', page.model_dump())

    info = browser_service.get_page_info(window_id)
    print('get_page_info ->', info.model_dump())

    closed = browser_service.close_browser(window_id)
    print('close_browser ->', closed.model_dump())


if __name__ == '__main__':
    main()
