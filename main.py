import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# --- Integration of your existing modules ---
# Ensure pii.py and db.py are in the same directory on GitHub
try:
    from pii import anonymize_text  # Your PII Protection Logic
    from db import save_log         # Your Database Logging Logic
except ImportError:
    # Fallback functions to prevent the server from crashing if files are missing
    def anonymize_text(text): return text, ["Module missing"]
    def save_log(data): print(f"Logging locally: {data}")

# --- API Configuration ---
app = FastAPI(
    title="🛡️ AI Shield Gateway",
    description="A secure enterprise-grade API for PII detection and redaction before AI processing.",
    version="1.0.0"
)

# --- Data Models ---
class ProtectionRequest(BaseModel):
    text_input: str
    user_id: Optional[str] = "default_user"

# --- Endpoints ---

@app.get("/", tags=["Health"])
def status():
    """Confirms the Gateway is active."""
    return {
        "status": "Online",
        "product": "AI Shield Gateway",
        "documentation": "/docs"
    }

@app.post("/process", tags=["Security Core"])
async def protect_data(request: ProtectionRequest):
    """
    The main product feature: 
    1. Receives raw text.
    2. Redacts sensitive PII (Emails, Phones, etc.).
    3. Saves the transaction to the database.
    4. Returns safe text for AI consumption.
    """
    try:
        # 1. Anonymization Layer
        redacted_text, detected_entities = anonymize_text(request.text_input)
        
        # 2. Prepare Log Data
        log_entry = {
            "user_id": request.user_id,
            "original_content": request.text_input,
            "redacted_content": redacted_text,
            "entities_found": str(detected_entities)
        }
        
        # 3. Save to SQLite Database
        save_log(log_entry)
        
        return {
            "original": request.text_input,
            "safe_output": redacted_text,
            "security_report": {
                "entities_found": len(detected_entities),
                "risk_types": detected_entities,
                "status": "Protected"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")

# --- Execution for Render ---
if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
