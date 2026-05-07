from app.schemas.browser import NewTabRequest
from app.schemas.desktop import ActivateWindowRequest
from app.services.browser_service import browser_service
from app.services.desktop_service import desktop_service


if __name__ == '__main__':
    opened = browser_service.open_browser()
    window_id = opened.windowId
    page = browser_service.new_tab(window_id, NewTabRequest(url='https://www.bing.com'))
    print('浏览器页面:', page)

    # 下面这段按需启用：激活浏览器窗口，再做桌面层操作
    # desktop_service.activate_window(ActivateWindowRequest(titleRegex='.*Chrome.*'))

    browser_service.close_browser(window_id)
