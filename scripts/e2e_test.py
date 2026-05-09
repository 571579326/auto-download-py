import requests
import json
import time

BASE = "http://localhost:7982/auto-download"

print("===== 步骤1: 健康检查 =====")
r = requests.get(f"{BASE}/health", timeout=5)
print(f"Status: {r.status_code}")
print(f"Body: {r.json()}")
print()

print("===== 步骤2: page-flow 完整流程 =====")
print("参数: configCode=acg18, imagePath=app/visual/templates/cf_check_dark.png, confidence=0.8")
print("正在执行 (可能需要数十秒)...")
print()

start = time.time()
try:
    r = requests.post(
        f"{BASE}/biz/page-flow",
        params={
            "configCode": "acg18",
            "imagePath": "app/visual/templates/cf_check_dark.png",
            "imageConfidence": 0.8,
            "pageStabilizeSeconds": 2.0,
        },
        timeout=120,
    )
    elapsed = time.time() - start
    print(f"耗时: {elapsed:.1f}s")
    print(f"HTTP Status: {r.status_code}")

    data = r.json()
    print(f"code: {data['code']}")
    print(f"message: {data['message']}")

    if data.get("data"):
        d = data["data"]
        print(f"  configCode  : {d.get('configCode')}")
        print(f"  windowId    : {d.get('windowId')}")
        print(f"  pagesOpened : {d.get('pagesOpened')}")
        print(f"  imageClicked: {d.get('imageClicked')}")

    print()
    print("===== 完整响应 JSON =====")
    print(json.dumps(data, ensure_ascii=False, indent=2))

except requests.exceptions.ConnectionError:
    print("连接失败: 服务未启动或端口不对")
except requests.exceptions.Timeout:
    elapsed = time.time() - start
    print(f"请求超时 ({elapsed:.0f}s)")
except Exception as e:
    elapsed = time.time() - start
    print(f"耗时: {elapsed:.1f}s")
    print(f"出错: {type(e).__name__}: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(f"Response body: {e.response.text[:1000]}")
