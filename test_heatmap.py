import requests
import json

# 测试 heatmap / correlation
url = "http://localhost:8000/api/chat/stream"

# 1) 3列全数值案例
body1 = {
    "question": "商品销量与价格的关系热力图"
}

print("=== Test 1: heatmap ===")
resp1 = requests.post(url, json=body1, stream=True, timeout=120)
resp1.raise_for_status()

buf = ""
for line in resp1.iter_lines():
    if line:
        try:
            s = line.decode('utf-8')
            if s.startswith("data: "):
                chunk = s[6:]
                if chunk == "[DONE]":
                    print("\n完成.")
                    break
                else:
                    print(chunk, end="", flush=True)
                    buf += chunk
        except Exception as e:
            print("异常：", e)

cevent = None
chart_found = False
for ev in buf.split("\n"):
    if not ev:
        continue
    try:
        obj = json.loads(ev)
        if obj.get("chart") and obj["chart"]["type"] in ["heatmap", "correlation"]:
            print("\n✅ 发现", obj["chart"]["type"], "图表")
            chart_found = True
    except Exception:
        pass
if not chart_found:
    print("\n❌ 没有找到 heatmap/correlation 图表")

print("\n=== Test 2: correlation ===")
body2 = {
    "question": "多变量相关性矩阵"
}
resp2 = requests.post(url, json=body2, stream=True, timeout=120)
resp2.raise_for_status()

buf2 = ""
for line in resp2.iter_lines():
    if line:
        try:
            s = line.decode('utf-8')
            if s.startswith("data: "):
                chunk = s[6:]
                if chunk == "[DONE]":
                    print("\n完成.")
                    break
                else:
                    print(chunk, end="", flush=True)
                    buf2 += chunk
        except Exception as e:
            print("异常：", e)

chart_found2 = False
for ev in buf2.split("\n"):
    if not ev:
        continue
    try:
        obj = json.loads(ev)
        if obj.get("chart") and obj["chart"]["type"] == "correlation":
            print("\n✅ 发现 correlation 图表")
            chart_found2 = True
    except Exception:
        pass
if not chart_found2:
    print("\n❌ 没有找到 correlation 图表")

print("\n== 测试完毕 =\n")