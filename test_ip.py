import urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/trending?limit=5') as response:
        print("127.0.0.1:", response.read().decode('utf-8'))
except Exception as e:
    print("127.0.0.1 Error:", e)

try:
    with urllib.request.urlopen('http://[::1]:8000/trending?limit=5') as response:
        print("[::1]:", response.read().decode('utf-8'))
except Exception as e:
    print("[::1] Error:", e)
