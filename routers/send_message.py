from fastapi import APIRouter
from pydantic import BaseModel
from telethon.errors import UsernameNotOccupiedError, ChatWriteForbiddenError
from telethon.tl.types import User, Chat, Channel
import asyncio
from typing import List
from datetime import datetime
from .session_manager import get_session

router = APIRouter()

class SendMessageRequest(BaseModel):
    session_name: str
    messages: List[str]

class SendMessageResponse(BaseModel):
    success: bool
    message: str
    responses: List[List[str]] = []
    error: str = None

@router.post("/api/fetch-data", response_model=SendMessageResponse)
async def send_message_and_scrape(request: SendMessageRequest):

    try:
        session_data = get_session(request.session_name)
        if not session_data:
            return SendMessageResponse(success=False, message="Session not found. Please integrate your Telegram account first.", error="Session not found")
        
        client = session_data["client"]
        target_username = session_data["target_username"]
        if not client.is_connected():
            await client.connect()
        try:
            target_entity = await client.get_entity(target_username)
        except UsernameNotOccupiedError:
            return SendMessageResponse(success=False, message=f"Target username '{target_username}' not found.", error="Username not found")
        responses = []
        my_id = (await client.get_me()).id
        for message in request.messages:
            try:
                last_messages = await client.get_messages(target_entity, limit=1)
                last_message_id = last_messages[0].id if last_messages else 0
                sent_message = await client.send_message(target_entity, message)
                await asyncio.sleep(5)
                messages_after = await client.get_messages(target_entity, limit=20, min_id=last_message_id)
                target_responses = []
                for msg in messages_after:
                    if msg.sender_id == my_id:
                        continue
                    if not msg.text:
                        continue
                    if msg.id == sent_message.id:
                        continue
                    target_responses.append({'text': msg.text, 'date': msg.date, 'id': msg.id})
                target_responses.sort(key=lambda x: x['date'])
                if target_responses:
                    response_texts = [resp['text'] for resp in target_responses]
                    responses.append(response_texts)
                else:
                    responses.append([])
            except ChatWriteForbiddenError:
                return SendMessageResponse(success=False, message=f"Cannot send message to '{target_username}'. User may have blocked you or doesn't allow messages.", error="Chat write forbidden")
            except Exception as e:
                responses.append([f"Error sending message '{message}': {str(e)}"])
        return SendMessageResponse(
            success=True,
            message=f"Successfully sent {len(request.messages)} messages to {target_username}",
            responses=responses,
        )
    except Exception as e:
        return SendMessageResponse(success=False, message=f"Failed to send messages: {str(e)}", error=str(e))