from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
import json
import os

app = FastAPI()

# Enable CORS for Vercel connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration - It's better to use Environment Variables on Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_gsk_key_here")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# PII Shield: Function to redact sensitive data
def screen_pii(text: str) -> str:
    # Redact Emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL_REDACTED]", text)
    # Redact Phone Numbers
    text = re.sub(r'\b(?:\+?\d{1,3}[- ]?)?\d{8,10}\b', "[PHONE_REDACTED]", text)
    return text

# 1. Models Endpoint (Fixes the "Not Found" /v1/models error)
@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "llama3-8b-8192", "object": "model", "owned_by": "groq"},
            {"id": "llama3-70b-8192", "object": "model", "owned_by": "groq"},
            {"id": "mixtral-8x7b-32768", "object": "model", "owned_by": "groq"}
        ]
    }

# 2. Chat Completions Endpoint (The core logic)
@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    body = await request.json()
    
    # Apply PII filter to user messages
    if "messages" in body:
        for msg in body["messages"]:
            if msg["role"] == "user":
                msg["content"] = screen_pii(msg["content"])

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", GROQ_URL, json=body, headers=headers, timeout=60.0) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    yield json.dumps({"error": "Groq API Error", "detail": error_detail.decode()}).encode()
                    return
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_generator(), media_type="application/json")

@app.get("/")
async def health_check():
    return {"status": "Active", "proxy": "AI Gateway", "security": "PII Filter Enabled"}
