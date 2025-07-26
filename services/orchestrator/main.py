#!/usr/bin/env python3
"""
Orchestrator service - FastAPI webhook handler for QStash
"""

from fastapi import FastAPI, Request, HTTPException
import os
import logging
import json
import jwt
import weaviate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QStash Pipeline Orchestrator")

# Environment variables
QSTASH_SIGNING_KEY = os.getenv("QSTASH_SIGNING_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")

# Initialize Weaviate client
weaviate_client = weaviate.Client(WEAVIATE_URL)

def verify_qstash_signature(request: Request, body: bytes):
    """Verify QStash JWT signature using EdDSA"""
    signature = request.headers.get("Upstash-Signature")
    
    if not signature:
        raise HTTPException(status_code=401, detail="Missing Upstash-Signature header")
    
    if not QSTASH_SIGNING_KEY:
        raise HTTPException(status_code=500, detail="QSTASH_SIGNING_KEY not configured")
    
    try:
        # Verify JWT signature with EdDSA algorithm
        decoded = jwt.decode(
            signature, 
            QSTASH_SIGNING_KEY, 
            algorithms=["EdDSA"]
        )
        logger.info(f"JWT signature verified: {decoded}")
        return decoded
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Weaviate connection
        weaviate_status = weaviate_client.is_ready()
        
        return {
            "status": "healthy", 
            "service": "orchestrator",
            "services": {
                "weaviate": "healthy" if weaviate_status else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "orchestrator", 
            "error": str(e)
        }

@app.post("/api/qstash")
async def qstash_webhook(request: Request):
    """QStash webhook handler with JWT verification"""
    body = await request.body()
    
    # Verify JWT signature
    jwt_payload = verify_qstash_signature(request, body)
    
    try:
        # Parse the webhook payload
        data = json.loads(body)
        logger.info(f"Processing QStash webhook: {data}")
        
        # Store in Weaviate RawURL class
        try:
            weaviate_client.batch.add_data_object(
                data_object=data,
                class_name="RawURL"
            )
            logger.info(f"Stored data in Weaviate: {data.get('id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to store in Weaviate: {e}")
            # Don't fail the webhook for storage errors
        
        return {"ok": True, "processed": data.get("id", "unknown")}
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)