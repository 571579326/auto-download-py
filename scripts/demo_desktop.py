from app.schemas.desktop import ActivateWindowRequest, HotkeyRequest, WindowQueryRequest
from app.services.desktop_service import desktop_service


if __name__ == '__main__':
    windows = desktop_service.list_windows(WindowQueryRequest(limit=10))
    print('窗口数量:', windows.total)
    for item in windows.windows:
        print(item)

    # 示例：按标题包含关键词激活窗口
    # resp = desktop_service.activate_window(ActivateWindowRequest(title='无标题 - 记事本'))
    # print(resp)

    # 示例：发送快捷键（请先确保目标窗口已激活）
    # desktop_service.hotkey(HotkeyRequest(keys=['ctrl', 'l']))
