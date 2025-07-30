from fastapi import APIRouter
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UsernameNotOccupiedError, ChatWriteForbiddenError
from telethon.tl.types import User, Chat, Channel
import asyncio
from typing import List
from .session_manager import add_session, get_active_sessions

router = APIRouter()

class TelegramIntegrationRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str
    target_username: str

class TelegramIntegrationResponse(BaseModel):
    success: bool
    message: str
    session_name: str = None

@router.post("/api/integrate_telegram", response_model=TelegramIntegrationResponse)
async def integrate_telegram(request: TelegramIntegrationRequest):
    try:
        session_name = f"session_{request.phone.replace('+', '').replace('-', '').replace(' ', '')}"
        client = TelegramClient(session_name, request.api_id, request.api_hash)
        await client.start(phone=request.phone)
        if not await client.is_user_authorized():
            return TelegramIntegrationResponse(success=False, message="Failed to authorize. Please check your credentials and try again.")
        me = await client.get_me()
        session_data = {
            "client": client,
            "phone": request.phone,
            "target_username": request.target_username,
            "user_info": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name
            }
        }
        add_session(session_name, session_data)
        return TelegramIntegrationResponse(success=True, message=f"Successfully integrated Telegram account for {me.first_name} ({me.username})", session_name=session_name)
    except SessionPasswordNeededError:
        return TelegramIntegrationResponse(success=False, message="Two-factor authentication is enabled. Please provide the password.")
    except PhoneCodeInvalidError:
        return TelegramIntegrationResponse(success=False, message="Invalid phone code provided.")
    except Exception as e:
        return TelegramIntegrationResponse(success=False, message=f"Integration failed: {str(e)}")

@router.get("/sessions")
async def get_active_sessions():
    sessions = []
    active_sessions = get_active_sessions()
    for session_name, session_data in active_sessions.items():
        sessions.append({
            "session_name": session_name,
            "phone": session_data["phone"],
            "target_username": session_data["target_username"],
            "user_info": session_data["user_info"]
        })
    return {"sessions": sessions}