from app.schemas.browser import NewTabRequest
from app.services.browser_service import browser_service


if __name__ == '__main__':
    opened = browser_service.open_browser()
    window_id = opened.windowId
    print('open_browser ->', opened.model_dump())
    page = browser_service.new_tab(window_id, NewTabRequest(url='https://www.bing.com'))
    print('new_tab ->', page.model_dump())
    print('pages ->', browser_service.list_pages(window_id).model_dump())
    print('close_browser ->', browser_service.close_browser(window_id).model_dump())
