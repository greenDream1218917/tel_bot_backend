from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UsernameNotOccupiedError, ChatWriteForbiddenError
from telethon.tl.types import User, Chat, Channel
import asyncio
import os
import json
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Telegram Bot Backend", description="Telegram integration API")

# Store active sessions
active_sessions = {}

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
    responses: List[List[str]] = []  # List of lists - each inner list contains all responses for one message
    error: str = None
    debug_info: dict = None

@app.post("/integrate_telegram", response_model=TelegramIntegrationResponse)
async def integrate_telegram(request: TelegramIntegrationRequest):
    """
    Integrate Telegram account using Telethon
    """
    try:
        # Create session name based on phone number
        session_name = f"session_{request.phone.replace('+', '').replace('-', '').replace(' ', '')}"
        
        # Create Telegram client
        client = TelegramClient(session_name, request.api_id, request.api_hash)
        
        # Start the client
        await client.start(phone=request.phone)
        
        # Check if we're authorized
        if not await client.is_user_authorized():
            return TelegramIntegrationResponse(
                success=False,
                message="Failed to authorize. Please check your credentials and try again."
            )
        
        # Test connection by getting our own user info
        me = await client.get_me()
        
        # Store the client in active sessions
        active_sessions[session_name] = {
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
        
        return TelegramIntegrationResponse(
            success=True,
            message=f"Successfully integrated Telegram account for {me.first_name} ({me.username})",
            session_name=session_name
        )
        
    except SessionPasswordNeededError:
        return TelegramIntegrationResponse(
            success=False,
            message="Two-factor authentication is enabled. Please provide the password."
        )
    except PhoneCodeInvalidError:
        return TelegramIntegrationResponse(
            success=False,
            message="Invalid phone code provided."
        )
    except Exception as e:
        return TelegramIntegrationResponse(
            success=False,
            message=f"Integration failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "Telegram Bot Backend is running"}

@app.get("/sessions")
async def get_active_sessions():
    """
    Get list of active Telegram sessions
    """
    sessions = []
    for session_name, session_data in active_sessions.items():
        sessions.append({
            "session_name": session_name,
            "phone": session_data["phone"],
            "target_username": session_data["target_username"],
            "user_info": session_data["user_info"]
        })
    return {"sessions": sessions}

@app.post("/send_message", response_model=SendMessageResponse)
async def send_message_and_scrape(request: SendMessageRequest):
    """
    Send messages to target user and scrape their responses
    """
    try:
        # Check if session exists
        if request.session_name not in active_sessions:
            return SendMessageResponse(
                success=False,
                message="Session not found. Please integrate your Telegram account first.",
                error="Session not found"
            )
        
        session_data = active_sessions[request.session_name]
        client = session_data["client"]
        target_username = session_data["target_username"]
        
        # Ensure client is connected
        if not client.is_connected():
            await client.connect()
        
        # Get target user/chat
        try:
            target_entity = await client.get_entity(target_username)
        except UsernameNotOccupiedError:
            return SendMessageResponse(
                success=False,
                message=f"Target username '{target_username}' not found.",
                error="Username not found"
            )
        
        responses = []
        
        # Get our own user ID for filtering
        my_id = (await client.get_me()).id
        
        # Send each message and wait for response
        for message in request.messages:
            try:
                # Get the last message ID before sending our message
                last_messages = await client.get_messages(target_entity, limit=1)
                last_message_id = last_messages[0].id if last_messages else 0
                
                # Send the message
                sent_message = await client.send_message(target_entity, message)
                
                # Wait for the response
                await asyncio.sleep(5)
                
                # Get messages that came after our sent message (using message ID)
                messages_after = await client.get_messages(
                    target_entity, 
                    limit=20,
                    min_id=last_message_id
                )
                
                # Filter for responses from target user only
                target_responses = []
                for msg in messages_after:
                    # Skip our own messages
                    if msg.sender_id == my_id:
                        continue
                    
                    # Skip messages without text
                    if not msg.text:
                        continue
                    
                    # Skip if it's our sent message
                    if msg.id == sent_message.id:
                        continue
                    
                    # This is a valid response from target user
                    target_responses.append({
                        'text': msg.text,
                        'date': msg.date,
                        'id': msg.id
                    })
                
                # Sort by date to get chronological order
                target_responses.sort(key=lambda x: x['date'])
                
                # Get ALL responses from target user (not just the first one)
                if target_responses:
                    # Extract all response texts in chronological order
                    response_texts = [resp['text'] for resp in target_responses]
                    responses.append(response_texts)
                else:
                    responses.append([])  # No responses received
                    
            except ChatWriteForbiddenError:
                return SendMessageResponse(
                    success=False,
                    message=f"Cannot send message to '{target_username}'. User may have blocked you or doesn't allow messages.",
                    error="Chat write forbidden"
                )
            except Exception as e:
                responses.append(f"Error sending message '{message}': {str(e)}")
        
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
        return SendMessageResponse(
            success=False,
            message=f"Failed to send messages: {str(e)}",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 