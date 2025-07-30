from fastapi import APIRouter
from pydantic import BaseModel
import requests
from typing import List, Dict, Any, Optional

router = APIRouter()

class Message(BaseModel):
    type: str
    content: str

class SendSignalRequest(BaseModel):
    BOT_TOKEN: str
    CHANNEL_USERNAME: str
    messages: List[Message]

class SendSignalResponse(BaseModel):
    success: bool
    error: Optional[str] = None

@router.post("/api/send-signal", response_model=SendSignalResponse)
async def send_signal(request: SendSignalRequest):
    try:
        successful_count = 0
        
        for msg in request.messages:
            try:
                # Prepare the message content
                if msg.type == "combined":
                    content = msg.content
                else:
                    content = f"[{msg.type.upper()}] {msg.content}"
                
                # Send message to Telegram channel
                send_message_url = f"https://api.telegram.org/bot{request.BOT_TOKEN}/sendMessage"
                send_data = {
                    "chat_id": request.CHANNEL_USERNAME,
                    "text": content,
                    "parse_mode": "HTML"  # Allow HTML formatting
                }
                
                response = requests.post(send_message_url, json=send_data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        successful_count += 1
                    
            except Exception as e:
                # Continue with next message if one fails
                continue
        
        if successful_count > 0:
            return SendSignalResponse(success=True)
        else:
            return SendSignalResponse(
                success=False,
                error="All messages failed to send"
            )
            
    except Exception as e:
        return SendSignalResponse(
            success=False,
            error=str(e)
        ) 