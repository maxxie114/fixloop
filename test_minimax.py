import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MINIMAX_API_KEY", "")
MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")
BASE_URL = "https://api.minimax.io/v1"


def test_minimax():
    print(f"Testing MiniMax API...")
    print(f"API Key: {API_KEY[:20]}..." if len(API_KEY) > 20 else f"API Key: {API_KEY}")
    print(f"Model: {MODEL}")
    print(f"Base URL: {BASE_URL}")
    print()

    if not API_KEY:
        print("ERROR: No API key found in .env file")
        return False

    prompt = "Say 'Hello, MiniMax API is working!' in a short sentence."

    try:
        response = httpx.post(
            f"{BASE_URL}/text/chatcompletion_v2",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
            timeout=30.0,
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                print(f"\nSUCCESS! Response: {content}")
                return True
            else:
                print("\nERROR: Empty response content")
                return False
        else:
            print(f"\nERROR: API returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        return False


if __name__ == "__main__":
    test_minimax()
