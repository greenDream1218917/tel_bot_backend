from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

# Import and include routers
from routers.telegram_integration import router as telegram_router
from routers.send_message import router as send_message_router
from routers.check_chatgpt import router as chatgpt_router
from routers.check_telegram_bot import router as telegram_bot_router
from routers.generate_message import router as generate_message_router
from routers.send_signal import router as send_signal_router

app.include_router(telegram_router)
app.include_router(send_message_router)
app.include_router(chatgpt_router)
app.include_router(telegram_bot_router)
app.include_router(generate_message_router)
app.include_router(send_signal_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Telegram Bot Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 