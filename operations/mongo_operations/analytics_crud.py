from configs.mongo_config import db
from datetime import datetime
from icecream import ic
import time

ANALYTICS_COLLECTION_NAME = "dauth_analytics"
AUDIT_LOGS_COLLECTION_NAME = "dauth_audit_logs"

async def log_auth_request(apikey: str, auth_method: str):
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        month = datetime.utcnow().strftime('%Y-%m')
        
        doc_id = f"{apikey}_{month}"
        
        await db[ANALYTICS_COLLECTION_NAME].update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "apikey": apikey,
                    "month": month
                },
                "$inc": {
                    "total_requests": 1,
                    f"methods.{auth_method}": 1,
                    f"daily.{today}.total_requests": 1,
                    f"daily.{today}.methods.{auth_method}": 1
                }
            },
            upsert=True
        )
    except Exception as e:
        ic(f"Error logging auth request: {e}")

async def log_sms_otp_dispatch(apikey: str):
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        month = datetime.utcnow().strftime('%Y-%m')
        
        doc_id = f"{apikey}_{month}"
        
        await db[ANALYTICS_COLLECTION_NAME].update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "apikey": apikey,
                    "month": month
                },
                "$inc": {
                    "sms_otp_count": 1,
                    f"daily.{today}.sms_otp_count": 1
                }
            },
            upsert=True
        )
    except Exception as e:
        ic(f"Error logging sms otp: {e}")

async def log_audit_event(apikey: str, ip_address: str, method: str, identifier: str, event_type: str, status: str):
    try:
        latest_event = await db[AUDIT_LOGS_COLLECTION_NAME].find_one(
            {"apikey": apikey, "identifier": identifier},
            sort=[("timestamp", -1)]
        )

        if event_type in ["LOGIN_SUCCESS", "LOGIN_FAILED"]:
            if latest_event and latest_event.get("status") == "Ongoing":
                await db[AUDIT_LOGS_COLLECTION_NAME].update_one(
                    {"_id": latest_event["_id"]},
                    {
                        "$set": {
                            "event_type": event_type,
                            "status": status,
                            "timestamp": time.time(),
                            "method": method
                        }
                    }
                )
                return

        if (latest_event and 
            latest_event.get("event_type") == event_type and 
            latest_event.get("ip_address") == ip_address and 
            latest_event.get("method") == method):
            
            await db[AUDIT_LOGS_COLLECTION_NAME].update_one(
                {"_id": latest_event["_id"]},
                {
                    "$inc": {"count": 1},
                    "$set": {
                        "timestamp": time.time(),
                        "created_at": datetime.utcnow(),
                        "status": status
                    }
                }
            )
        else:
            await db[AUDIT_LOGS_COLLECTION_NAME].insert_one({
                "apikey": apikey,
                "timestamp": time.time(),
                "ip_address": ip_address,
                "method": method,
                "identifier": identifier,
                "event_type": event_type,
                "status": status,
                "count": 1,
                "created_at": datetime.utcnow()
            })
    except Exception as e:
        ic(f"Error logging audit event: {e}")
