import urllib.request
import json
import sys

req = urllib.request.Request(
    'http://127.0.0.1:8000/chat',
    data=json.dumps({"message": "Hello", "model": "llama", "disease_name": "alzheimer"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            sys.stdout.buffer.write(line)
            sys.stdout.flush()
        print("\nSuccess")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
