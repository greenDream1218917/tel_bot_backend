from fastapi import APIRouter
from pydantic import BaseModel
from telethon.errors import UsernameNotOccupiedError, ChatWriteForbiddenError
from telethon.tl.types import User, Chat, Channel
import asyncio
from typing import List
from datetime import datetime

router = APIRouter()

# This should be imported/shared from telegram_integration
active_sessions = {}

class SendMessageRequest(BaseModel):
    session_name: str
    messages: List[str]

class SendMessageResponse(BaseModel):
    success: bool
    message: str
    responses: List[List[str]] = []
    error: str = None
    debug_info: dict = None

@router.post("/send_message", response_model=SendMessageResponse)
async def send_message_and_scrape(request: SendMessageRequest):
    try:
        if request.session_name not in active_sessions:
            return SendMessageResponse(success=False, message="Session not found. Please integrate your Telegram account first.", error="Session not found")
        session_data = active_sessions[request.session_name]
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
            debug_info={
                "target_username": target_username,
                "my_user_id": my_id,
                "messages_sent": len(request.messages),
                "responses_found": sum(len(r) for r in responses),
                "total_response_groups": len([r for r in responses if r]),
                "target_entity_type": str(type(target_entity)),
                "wait_time_seconds": 5
            }
        )
    except Exception as e:
        return SendMessageResponse(success=False, message=f"Failed to send messages: {str(e)}", error=str(e))