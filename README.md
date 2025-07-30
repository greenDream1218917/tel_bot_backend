# Telegram Bot Backend

A FastAPI-based backend for Telegram integration using Telethon library.

## Features

- Telegram account integration using Telethon
- Session management for multiple accounts
- RESTful API endpoints

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Get Telegram API credentials:
   - Go to https://my.telegram.org/
   - Log in with your phone number
   - Create a new application
   - Note down your `api_id` and `api_hash`

3. Run the application:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### 1. Integrate Telegram Account
**POST** `/integrate_telegram`

Integrate your Telegram account using Telethon.

**Request Body:**
```json
{
    "api_id": 123456,
    "api_hash": "your_api_hash_here",
    "phone": "+1234567890",
    "target_username": "target_user"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully integrated Telegram account for John Doe (@johndoe)",
    "session_name": "session_1234567890"
}
```

### 2. Health Check
**GET** `/health`

Check if the API is running.

### 3. Get Active Sessions
**GET** `/sessions`

Get list of all active Telegram sessions.

### 4. Send Messages and Scrape Responses
**POST** `/send_message`

Send messages to target user and scrape their responses.

**Request Body:**
```json
{
    "session_name": "session_1234567890",
    "messages": ["/btc", "/top_15m", "/eth"]
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully sent 3 messages to target_user",
    "responses": [
        [
            "hi",
            "I am developer",
            "How can I help you?"
        ],
        [
            "Bitcoin price: $45,000",
            "Current trend: Bullish"
        ],
        [
            "Top 15m signals: BTC/USDT - BUY at $44,500"
        ]
    ],
    "error": null
}
```

## Usage Example

```python
import requests

# Integrate Telegram account
response = requests.post("http://localhost:8000/integrate_telegram", json={
    "api_id": 123456,
    "api_hash": "your_api_hash_here",
    "phone": "+1234567890",
    "target_username": "target_user"
})

print(response.json())

# Send messages and scrape responses
session_name = response.json()["session_name"]
send_response = requests.post("http://localhost:8000/send_message", json={
    "session_name": session_name,
    "messages": ["/btc", "/top_15m", "/eth"]
})

result = send_response.json()
print("All responses:", result["responses"])

# Access individual responses
for i, response_group in enumerate(result["responses"]):
    print(f"Responses to message {i+1}: {response_group}")
```

## Notes

- The first time you integrate an account, you'll need to provide the verification code sent to your phone
- Session files are stored locally and will be reused for subsequent requests
- Make sure to keep your API credentials secure
- The target_username is stored for future use in message scraping

## Error Handling

The API handles various error scenarios:
- Invalid API credentials
- Phone verification code errors
- Two-factor authentication requirements
- Network connectivity issues 