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

USER_COLLECTION_NAME = "dauth_users"
INVOICES_COLLECTION_NAME = "dauth_invoices"

async def check_and_generate_sms_invoices():
    """
    Checks each user's SMS OTP dispatch count for the current month.
    Generates a monthly SMS OTP usage invoice at ₹0.40 / SMS OTP.
    Whitelisted emails in OTP_COST_WHITELIST are completely exempt (no invoices generated).
    """
    try:
        now = datetime.utcnow()
        current_month = now.strftime('%Y-%m')

        cursor = db[USER_COLLECTION_NAME].find()
        async for user in cursor:
            email = user.get('email')
            if not email:
                continue

            # Check if user email is whitelisted from OTP costs
            if settings.is_otp_cost_exempt(email):
                continue

            # Check if invoice for this month's SMS OTP was already generated
            existing_invoice = await db[INVOICES_COLLECTION_NAME].find_one({
                "user_email": email,
                "description": {"$regex": f"SMS OTP.*{current_month}"}
            })
            if existing_invoice:
                continue

            # Calculate total SMS OTPs sent across all API keys belonging to this user
            secrets = user.get('secrets', {})
            total_sms = 0
            for apikey in secrets.keys():
                analytics_doc = await db["dauth_analytics"].find_one({"_id": f"{apikey}_{current_month}"})
                if analytics_doc:
                    total_sms += analytics_doc.get("sms_otp_count", 0)

            if total_sms > 0:
                cost = round(total_sms * 0.40, 2)
                await create_invoice(
                    user_email=email,
                    amount=cost,
                    description=f"Monthly SMS OTP Usage ({current_month}) - {total_sms} SMS",
                    status="pending",
                    razorpay_order_id=f"sms_{current_month}_{int(now.timestamp())}",
                    invoice_type="otp"
                )
                ic(f"Generated SMS OTP invoice of ₹{cost} for {email}")
    except Exception as e:
        ic(f"Error in SMS OTP billing cron: {e}")
