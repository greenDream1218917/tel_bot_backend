from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UsernameNotOccupiedError, ChatWriteForbiddenError
from telethon.tl.types import User, Chat, Channel
import asyncio
import os
import json
import requests
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

app = FastAPI(title="Telegram Bot Backend", description="Telegram integration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class ChatGPTCheckRequest(BaseModel):
    api_key: str

class ChatGPTCheckResponse(BaseModel):
    success: bool
    message: str
    error: str = None

class TelegramBotCheckRequest(BaseModel):
    bot_token: str
    channel_id: str

class TelegramBotCheckResponse(BaseModel):
    success: bool
    message: str
    error: str = None

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

@app.post("/api/check-openai", response_model=ChatGPTCheckResponse)
async def check_openai(request: ChatGPTCheckRequest):
    """
    Check ChatGPT API interaction
    """
    try:
        # Test ChatGPT API with a simple request
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Hello, this is a test message. Please respond with 'API test successful'."}
            ],
            "max_tokens": 50
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={**headers, "Authorization": f"Bearer {request.api_key}"},
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return ChatGPTCheckResponse(
                success=True,
                message="ChatGPT API interaction successful"
            )
        else:
            error_detail = response.json().get('error', {}).get('message', 'Unknown error')
            return ChatGPTCheckResponse(
                success=False,
                message=f"ChatGPT API interaction failed: {error_detail}",
                error=f"HTTP {response.status_code}: {error_detail}"
            )
            
    except requests.exceptions.RequestException as e:
        return ChatGPTCheckResponse(
            success=False,
            message=f"Network error while checking ChatGPT API: {str(e)}",
            error=str(e)
        )
    except Exception as e:
        return ChatGPTCheckResponse(
            success=False,
            message=f"Error checking ChatGPT API: {str(e)}",
            error=str(e)
        )

@app.post("/check_telegram_bot", response_model=TelegramBotCheckResponse)
async def check_telegram_bot(request: TelegramBotCheckRequest):
    """
    Check Telegram Bot API interaction
    """
    try:
        # Test Telegram Bot API by getting bot info
        bot_info_url = f"https://api.telegram.org/bot{request.bot_token}/getMe"
        bot_info_response = requests.get(bot_info_url, timeout=30)
        
        if bot_info_response.status_code != 200:
            return TelegramBotCheckResponse(
                success=False,
                message=f"Telegram Bot API check failed: Invalid bot token",
                error=f"HTTP {bot_info_response.status_code}: Invalid bot token"
            )
        
        bot_info = bot_info_response.json()
        if not bot_info.get('ok'):
            return TelegramBotCheckResponse(
                success=False,
                message=f"Telegram Bot API check failed: {bot_info.get('description', 'Unknown error')}",
                error=bot_info.get('description', 'Unknown error')
            )
        
        # Test sending a message to the channel (this will fail if bot doesn't have permission, but we can check if the API works)
        send_message_url = f"https://api.telegram.org/bot{request.bot_token}/sendMessage"
        send_data = {
            "chat_id": request.channel_id,
            "text": "Bot API test message - this is a test to verify bot permissions."
        }
        
        send_response = requests.post(send_message_url, json=send_data, timeout=30)
        
        if send_response.status_code == 200:
            send_result = send_response.json()
            if send_result.get('ok'):
                return TelegramBotCheckResponse(
                    success=True,
                    message=f"Telegram Bot API interaction successful. Bot: @{bot_info['result']['username']}"
                )
            else:
                return TelegramBotCheckResponse(
                    success=False,
                    message=f"Telegram Bot API interaction failed: {send_result.get('description', 'Unknown error')}",
                    error=send_result.get('description', 'Unknown error')
                )
        else:
            return TelegramBotCheckResponse(
                success=False,
                message=f"Telegram Bot API interaction failed: HTTP {send_response.status_code}",
                error=f"HTTP {send_response.status_code}"
            )
            
    except requests.exceptions.RequestException as e:
        return TelegramBotCheckResponse(
            success=False,
            message=f"Network error while checking Telegram Bot API: {str(e)}",
            error=str(e)
        )
    except Exception as e:
        return TelegramBotCheckResponse(
            success=False,
            message=f"Error checking Telegram Bot API: {str(e)}",
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 