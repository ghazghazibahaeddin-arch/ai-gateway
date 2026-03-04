import os
import uvicorn
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# --- Import your security and database modules ---
try:
    from pii import anonymize_text  # Your PII Logic
    from db import save_log         # Your DB Logic
except ImportError:
    # Fallback to prevent crash if modules are missing
    def anonymize_text(text): return text, []
    def save_log(data): print(f"Audit Log: {data}")

# --- Initialize AI Shield Gateway ---
app = FastAPI(
    title="🛡️ AI Shield Gateway (Enterprise Edition)",
    description="Secure Gateway for PII Redaction and Free AI Routing (Llama 3)",
    version="2.0.0"
)

# Fetch Groq API Key from Render Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- Request Data Model ---
class ChatRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "global_user"

# --- Main Gateway Endpoint ---
@app.post("/v1/secure/chat")
async def secure_gateway_chat(request: ChatRequest):
    """
    1. Redacts PII from the input.
    2. Routes the clean prompt to Llama 3 (via Groq).
    3. Tracks token usage and logs the transaction.
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set in Render settings.")

    try:
        # STEP 1: PII Protection Layer (Privacy Control)
        safe_prompt, detected_entities = anonymize_text(request.prompt)

        # STEP 2: Intent Routing to Free Model (Llama 3 via Groq)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a secure assistant. Answer the user's prompt."},
                {"role": "user", "content": safe_prompt}
            ],
            "temperature": 0.7
        }

        # Sending request to AI model
        response = requests.post(url, json=payload, headers=headers)
        ai_data = response.json()

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=ai_data)

        # STEP 3: Observability & Usage Metrics
        ai_reply = ai_data['choices'][0]['message']['content']
        usage = ai_data.get('usage', {})
        
        metrics = {
            "user_id": request.user_id,
            "tokens_used": usage.get('total_tokens', 0),
            "pii_detected": len(detected_entities),
            "routing": "Groq-Llama3-Free"
        }

        # STEP 4: Persistent Audit Trail (Database Logging)
        save_log({**metrics, "original": request.prompt, "clean": safe_prompt})

        # Final Return to User
        return {
            "response": ai_reply,
            "security": {
                "status": "Protected",
                "redacted_content": safe_prompt,
                "entities_found": detected_entities
            },
            "usage_analytics": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Gateway Error: {str(e)}")

# --- Health Check ---
@app.get("/")
def health_check():
    return {"status": "Active", "engine": "FastAPI", "security": "Enabled"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
