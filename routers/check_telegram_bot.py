from fastapi import APIRouter
from pydantic import BaseModel
import requests

router = APIRouter()

class TelegramBotCheckRequest(BaseModel):
    bot_token: str
    channel_id: str

class TelegramBotCheckResponse(BaseModel):
    success: bool
    message: str
    error: str = None

@router.post("/check_telegram_bot", response_model=TelegramBotCheckResponse)
async def check_telegram_bot(request: TelegramBotCheckRequest):
    try:
        bot_info_url = f"https://api.telegram.org/bot{request.bot_token}/getMe"
        bot_info_response = requests.get(bot_info_url, timeout=30)
        if bot_info_response.status_code != 200:
            return TelegramBotCheckResponse(success=False, message=f"Telegram Bot API check failed: Invalid bot token", error=f"HTTP {bot_info_response.status_code}: Invalid bot token")
        bot_info = bot_info_response.json()
        if not bot_info.get('ok'):
            return TelegramBotCheckResponse(success=False, message=f"Telegram Bot API check failed: {bot_info.get('description', 'Unknown error')}", error=bot_info.get('description', 'Unknown error'))
        send_message_url = f"https://api.telegram.org/bot{request.bot_token}/sendMessage"
        send_data = {
            "chat_id": request.channel_id,
            "text": "Bot API test message - this is a test to verify bot permissions."
        }
        send_response = requests.post(send_message_url, json=send_data, timeout=30)
        if send_response.status_code == 200:
            send_result = send_response.json()
            if send_result.get('ok'):
                return TelegramBotCheckResponse(success=True, message=f"Telegram Bot API interaction successful. Bot: @{bot_info['result']['username']}")
            else:
                return TelegramBotCheckResponse(success=False, message=f"Telegram Bot API interaction failed: {send_result.get('description', 'Unknown error')}", error=send_result.get('description', 'Unknown error'))
        else:
            return TelegramBotCheckResponse(success=False, message=f"Telegram Bot API interaction failed: HTTP {send_response.status_code}", error=f"HTTP {send_response.status_code}")
    except requests.exceptions.RequestException as e:
        return TelegramBotCheckResponse(success=False, message=f"Network error while checking Telegram Bot API: {str(e)}", error=str(e))
    except Exception as e:
        return TelegramBotCheckResponse(success=False, message=f"Error checking Telegram Bot API: {str(e)}", error=str(e))