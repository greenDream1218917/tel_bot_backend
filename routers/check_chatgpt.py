from fastapi import APIRouter
from pydantic import BaseModel
import requests

router = APIRouter()

class ChatGPTCheckRequest(BaseModel):
    api_key: str

class ChatGPTCheckResponse(BaseModel):
    success: bool
    message: str
    error: str = None

@router.post("/api/check-openai", response_model=ChatGPTCheckResponse)
async def check_openai(request: ChatGPTCheckRequest):
    try:
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
            return ChatGPTCheckResponse(success=True, message="ChatGPT API interaction successful")
        else:
            error_detail = response.json().get('error', {}).get('message', 'Unknown error')
            return ChatGPTCheckResponse(success=False, message=f"ChatGPT API interaction failed: {error_detail}", error=f"HTTP {response.status_code}: {error_detail}")
    except requests.exceptions.RequestException as e:
        return ChatGPTCheckResponse(success=False, message=f"Network error while checking ChatGPT API: {str(e)}", error=str(e))
    except Exception as e:
        return ChatGPTCheckResponse(success=False, message=f"Error checking ChatGPT API: {str(e)}", error=str(e))