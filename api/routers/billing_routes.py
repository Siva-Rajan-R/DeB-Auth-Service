from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from api.dependencies.auth_state import get_and_validate_auth_state
from api.routers.deb_user_routes import verify_user
from services.razorpay_service import create_order, verify_payment_signature
from operations.mongo_operations.billing_crud import create_or_update_subscription, get_subscription, get_user_invoices, create_invoice, SUBSCRIPTIONS_COLLECTION_NAME
from configs.mongo_config import db
from services.email_service.main import send_email
from datetime import datetime, timedelta
from icecream import ic
import hmac
import hashlib
import os

router = APIRouter(
    tags=["Billing & Subscriptions"]
)

class SubscriptionCreateSchema(BaseModel):
    plan_name: str
    amount: float

class PaymentVerifySchema(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_name: str

@router.get("/billing/subscription")
async def get_current_subscription(user_email: str = Depends(verify_user)):
    return await get_subscription(user_email)

@router.get("/billing/invoices")
async def get_invoices(user_email: str = Depends(verify_user)):
    return await get_user_invoices(user_email)

@router.post("/billing/subscribe/create_order")
async def subscribe_create_order(inp: SubscriptionCreateSchema, user_email: str = Depends(verify_user)):
    order = create_order(amount=inp.amount, receipt=f"sub_{user_email}")
    if not order:
        raise HTTPException(status_code=500, detail="Failed to create Razorpay order")
    return {"order_id": order["id"], "amount": order["amount"], "currency": order["currency"]}

@router.post("/billing/subscribe/verify")
async def subscribe_verify(inp: PaymentVerifySchema, user_email: str = Depends(verify_user)):
    is_valid = verify_payment_signature(
        razorpay_order_id=inp.razorpay_order_id,
        razorpay_payment_id=inp.razorpay_payment_id,
        razorpay_signature=inp.razorpay_signature
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    await create_or_update_subscription(
        email=user_email,
        plan=inp.plan_name,
        razorpay_subscription_id=inp.razorpay_order_id
    )
    return {"message": "Subscription activated successfully"}

@router.post("/billing/subscribe/cancel")
async def cancel_subscription(user_email: str = Depends(verify_user)):
    await create_or_update_subscription(user_email, "Community", None)
    return {"message": "Successfully downgraded to Community plan"}

@router.post("/billing/webhook")
async def razorpay_webhook(request: Request):
    # Webhook signature validation
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        return {"status": "ok", "message": "Webhook skipped, no secret"}

    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    expected_signature = hmac.new(
        key=webhook_secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    # Process payload if necessary (e.g. invoice paid)
    return {"status": "ok"}

@router.post("/billing/simulate/expire")
async def simulate_subscription_expiration(user_email: str = Depends(verify_user), bgt: BackgroundTasks = None):
    # 1. Update subscription status
    await db[SUBSCRIPTIONS_COLLECTION_NAME].update_one(
        {"_id": user_email},
        {"$set": {
            "status": "grace_period",
            "current_period_end": datetime.utcnow() - timedelta(days=1)
        }}
    )
    
    # 2. Create a pending invoice (mock amount)
    amount = 499.0
    await create_invoice(user_email, amount, "Subscription Renewal - Grace Period", "pending", f"mock_order_{int(datetime.utcnow().timestamp())}")
    
    # 3. Send email
    html_body = f"""
    <h2>Subscription Expired - Grace Period Started</h2>
    <p>Your subscription has expired. You are now in a 3-day grace period.</p>
    <p>Please pay your pending invoice of ₹{amount} to avoid service interruption.</p>
    """
    if bgt:
        bgt.add_task(send_email, [user_email], "Action Required: Subscription Expired", html_body, True)
        
    return {"message": "Simulation triggered successfully. Check your email (or mock email) for the invoice."}
