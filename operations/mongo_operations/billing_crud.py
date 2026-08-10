from configs.mongo_config import db
from icecream import ic
from datetime import datetime, timedelta
from configs.settings import settings

SUBSCRIPTIONS_COLLECTION_NAME = "dauth_subscriptions"
INVOICES_COLLECTION_NAME = "dauth_invoices"

async def get_subscription(email: str):
    sub = await db[SUBSCRIPTIONS_COLLECTION_NAME].find_one({"_id": email})
    
    if settings.MOCK_SUBSCRIPTION_STATE != "none":
        mock_state = settings.MOCK_SUBSCRIPTION_STATE
        sub = sub or {"plan": "Growth", "status": "active"}
        if mock_state == "ending_soon":
            sub["status"] = "active"
            sub["current_period_end"] = datetime.utcnow() + timedelta(days=2)
        elif mock_state == "grace_period":
            sub["status"] = "grace_period"
            sub["current_period_end"] = datetime.utcnow() - timedelta(days=1)
        elif mock_state == "expired":
            sub["status"] = "expired"
            sub["current_period_end"] = datetime.utcnow() - timedelta(days=10)
        return sub
        
    if not sub:
        return {"plan": "Community", "status": "active"}
    return sub

async def create_or_update_subscription(email: str, plan: str, razorpay_subscription_id: str = None):
    try:
        await db[SUBSCRIPTIONS_COLLECTION_NAME].update_one(
            {"_id": email},
            {"$set": {
                "plan": plan,
                "razorpay_subscription_id": razorpay_subscription_id,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
    except Exception as e:
        ic(f"Error updating subscription: {e}")

async def create_invoice(user_email: str, amount: float, description: str, status: str = "pending", razorpay_order_id: str = None):
    try:
        doc = {
            "user_email": user_email,
            "amount": amount,
            "description": description,
            "status": status,
            "razorpay_order_id": razorpay_order_id,
            "created_at": datetime.utcnow()
        }
        await db[INVOICES_COLLECTION_NAME].insert_one(doc)
    except Exception as e:
        ic(f"Error creating invoice: {e}")

async def update_invoice_status(razorpay_order_id: str, status: str):
    try:
        await db[INVOICES_COLLECTION_NAME].update_one(
            {"razorpay_order_id": razorpay_order_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
    except Exception as e:
        ic(f"Error updating invoice: {e}")

async def get_user_invoices(email: str):
    try:
        cursor = db[INVOICES_COLLECTION_NAME].find({"user_email": email}).sort("created_at", -1)
        invoices = await cursor.to_list(length=100)
        # Convert ObjectId to string for JSON serialization
        for inv in invoices:
            inv["_id"] = str(inv["_id"])
        return invoices
    except Exception as e:
        ic(f"Error fetching invoices: {e}")
        return []
