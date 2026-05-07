import requests

BASE = 'http://127.0.0.1:7982/auto-download'

open_resp = requests.post(f'{BASE}/browser/session/open', timeout=30)
print('open:', open_resp.status_code, open_resp.text)
open_resp.raise_for_status()

window_id = open_resp.json()['data']['windowId']

pages_resp = requests.get(f'{BASE}/browser/pages', params={'windowId': window_id}, timeout=30)
print('pages:', pages_resp.status_code, pages_resp.text)

close_resp = requests.post(f'{BASE}/browser/close', params={'windowId': window_id}, timeout=30)
print('close:', close_resp.status_code, close_resp.text)
