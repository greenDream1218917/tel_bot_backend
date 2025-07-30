from pydantic import BaseModel
from typing import List, Optional, Dict

class TelegramIntegrationRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str
    target_username: str

class TelegramIntegrationResponse(BaseModel):
    success: bool
    message: str
    session_name: str = None

class SendMessageRequest(BaseModel):
    session_name: str
    messages: List[str]

class SendMessageResponse(BaseModel):
    success: bool
    message: str
    responses: List[List[str]] = []
    error: Optional[str] = None
    debug_info: Optional[Dict] = None

class ChatGPTCheckRequest(BaseModel):
    api_key: str

class ChatGPTCheckResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

class TelegramBotCheckRequest(BaseModel):
    bot_token: str
    channel_id: str

class TelegramBotCheckResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None