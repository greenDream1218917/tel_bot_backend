from fastapi import APIRouter
from pydantic import BaseModel
import requests
from typing import Optional

router = APIRouter()

class GenerateMessageRequest(BaseModel):
    api_key: str
    prompt: str

class GenerateMessageResponse(BaseModel):
    success: bool
    message: str
    generated_text: Optional[str] = None
    error: Optional[str] = None

@router.post("/api/generate-message", response_model=GenerateMessageResponse)
async def generate_message(request: GenerateMessageRequest):
    try:
        headers = {
            "Authorization": f"Bearer {request.api_key}",
            "Content-Type": "application/json"
        }
        
        # Create the full prompt by combining the prompt template with the data
        prompt = request.prompt
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['choices'][0]['message']['content']
            print(generated_text)
            return GenerateMessageResponse(
                success=True,
                message="Message generated successfully",
                generated_text=generated_text
            )
        else:
            error_detail = response.json().get('error', {}).get('message', 'Unknown error')
            return GenerateMessageResponse(
                success=False,
                message=f"Failed to generate message: {error_detail}",
                error=f"HTTP {response.status_code}: {error_detail}"
            )
            
    except requests.exceptions.RequestException as e:
        return GenerateMessageResponse(
            success=False,
            message=f"Network error while generating message: {str(e)}",
            error=str(e)
        )
    except Exception as e:
        return GenerateMessageResponse(
            success=False,
            message=f"Error generating message: {str(e)}",
            error=str(e)
        ) 