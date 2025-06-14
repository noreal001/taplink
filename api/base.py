from loader import *
from utils import *
from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import hmac
import hashlib
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

WEBHOOK_SECRET = "phrase"

class Record(BaseModel):
    value: str
    type: int
    title: str

class RecordsExtended(BaseModel):
    name: str
    type: str
    value: str

class Offer(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    # Add other offer fields as needed

class Shipping(BaseModel):
    price: Optional[float] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    addr1: Optional[str] = None
    shipping_method: Optional[str] = None

class WebhookData(BaseModel):
    profile_id: str
    username: str
    name: str
    email: str
    phone: str
    status_id: Optional[int] = None
    contact_id: str
    block_id: Optional[str] = None
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    order_status_id: Optional[int] = None
    purpose: Optional[str] = None
    tms_modify: Optional[str] = None
    budget: Optional[float] = None
    currency_code: Optional[str] = None
    currency_title: Optional[str] = None
    page_link: str
    lead_id: str
    ip: str
    lead_number: str
    tms_created: str
    records: List[Record]
    records_extended: Optional[List[RecordsExtended]] = None
    offers: Optional[List[Offer]] = None
    discounts: Optional[List[Dict[str, Any]]] = None
    shipping: Optional[Shipping] = None

class WebhookPayload(BaseModel):
    action: str  # e.g., "leads.created" or "payments.created"
    data: WebhookData

@app.get("/")
async def root():
    logger.info("Обработан запрос к корневому URL")
    return {"message": "Hello World"}

def verify_signature(signature: str, payload: bytes) -> bool:
    """
    Verify the Taplink webhook signature.
    """
    if not WEBHOOK_SECRET:
        raise ValueError("Webhook secret is not configured")
    
    digest = hmac.new(
        WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha1
    ).hexdigest()
    
    return hmac.compare_digest(digest, signature)

@app.post("/webhook/taplink")
async def handle_taplink_webhook(request: Request):
    try:
        # Get the raw body payload
        payload = await request.body()
        
        # Get the signature from headers
        signature = request.headers.get("taplink-signature")
        if not signature:
            logger.error("Missing taplink-signature header")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing taplink-signature header"
            )
        
        # Verify the signature
        if not verify_signature(signature, payload):
            logger.error("Invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Parse the JSON payload
        try:
            webhook_data = await request.json()
            payload_model = WebhookPayload(**webhook_data)
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload: {str(e)}"
            )
        
        logger.info(f"Received webhook with action: {payload_model.action}")
        logger.info(f"Webhook data: {webhook_data}")
        
        # Process different webhook actions
        if payload_model.action == "leads.created":
            # Handle new lead
            logger.info("Processing new lead")
            await process_new_lead(payload_model.data)
        elif payload_model.action == "payments.created":
            # Handle new payment
            logger.info("Processing new payment")
            await process_new_payment(payload_model.data)
        else:
            logger.warning(f"Unknown action received: {payload_model.action}")
        
        return JSONResponse(content={"status": "success"}, status_code=200)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )

async def process_new_lead(data: WebhookData):
    """
    Process a new lead from Taplink.
    """
    # Implement your lead processing logic here
    logger.info(f"New lead received - ID: {data.lead_id}, Name: {data.name}")
    logger.info(f"Lead details: {data}")
    
    # Example: Save to database, send notification, etc.
    # ...

async def process_new_payment(data: WebhookData):
    """
    Process a new payment from Taplink.
    """
    if data.order_status_id is None:
        logger.warning("Payment data missing order_status_id")
        return
    
    logger.info(f"New payment received - Order: {data.order_number}, Status: {data.order_status_id}")
    logger.info(f"Payment amount: {data.budget} {data.currency_title}")
    
    # Check payment status
    if data.order_status_id == 2:  # Paid
        logger.info("Payment confirmed - processing order")
        # Implement your payment processing logic here
        # ...
    elif data.order_status_id == 3:  # Canceled
        logger.info("Payment was canceled")
        # Handle canceled payment
        # ...
    else:
        logger.info(f"Payment status: {data.order_status_id} - no action taken")