import asyncio
from datetime import datetime, timedelta
from configs.mongo_config import db
from icecream import ic
from operations.mongo_operations.billing_crud import SUBSCRIPTIONS_COLLECTION_NAME, create_invoice
from services.email_service.main import send_email
from configs.settings import settings

async def check_and_notify_subscriptions():
    try:
        ic("Running subscription cron job...")
        
        # In a real system, you might only run this once a day. For now, it runs periodically.
        cursor = db[SUBSCRIPTIONS_COLLECTION_NAME].find({
            "plan": {"$ne": "Community"},
            "status": {"$ne": "expired"}
        })
        
        now = datetime.utcnow()
        grace_period_days = settings.GRACE_PERIOD_DAYS
        
        async for sub in cursor:
            email = sub.get("_id")
            if not email:
                continue
                
            current_end = sub.get("current_period_end")
            status = sub.get("status", "active")
            plan = sub.get("plan")
            
            # If there's no expiration date, skip
            if not current_end:
                continue
                
            # Check for transition to grace period
            if status == "active" and current_end <= now:
                await db[SUBSCRIPTIONS_COLLECTION_NAME].update_one(
                    {"_id": email},
                    {"$set": {"status": "grace_period"}}
                )
                
                # Send email
                html_body = f"""
                <h2>Action Required: Subscription Grace Period</h2>
                <p>Your {plan} subscription has ended. You are now in a {grace_period_days}-day grace period.</p>
                <p>Please renew your subscription to avoid service interruption.</p>
                """
                asyncio.create_task(send_email([email], "Action Required: Subscription Grace Period", html_body, True))
                ic(f"Subscription {email} moved to grace_period.")
                
            # Check for transition from grace period to expired
            elif status == "grace_period" and (now - current_end).days > grace_period_days:
                await db[SUBSCRIPTIONS_COLLECTION_NAME].update_one(
                    {"_id": email},
                    {"$set": {"status": "expired"}}
                )
                
                html_body = f"""
                <h2>Subscription Expired</h2>
                <p>Your grace period has ended and your {plan} subscription is now expired.</p>
                <p>Your account will be downgraded to the Community tier limitations.</p>
                """
                asyncio.create_task(send_email([email], "Notice: Subscription Expired", html_body, True))
                ic(f"Subscription {email} moved to expired.")
                
    except Exception as e:
        ic(f"Error in subscription cron job: {e}")
