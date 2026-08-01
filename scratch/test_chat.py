import urllib.request
import json
import sys

def test_chat(debug_flag):
    url = 'http://localhost:8000/api/v1/chat'
    data = json.dumps({
        "message": "tell me about a pop song",
        "debug": debug_flag
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"DEBUG MODE: {debug_flag}")
            print(f"Message: {result.get('assistant_message', '')[:100]}...")
            print(f"Citations length: {len(result.get('citations', []))}")
            print(f"Tool calls length: {len(result.get('tool_calls', []))}")
            print(f"Latency data: {result.get('latency_ms', {})}")
            print("-" * 40)
    except Exception as e:
        print(f"Error testing debug={debug_flag}: {e}")

if __name__ == "__main__":
    test_chat(False)
    test_chat(True)
