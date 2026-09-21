from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from api.routers.deb_user_routes import verify_user
from configs.mongo_config import db
from datetime import datetime
from dateutil.relativedelta import relativedelta
from icecream import ic
from operations.mongo_operations.analytics_crud import AUDIT_LOGS_COLLECTION_NAME
from operations.mongo_operations.billing_crud import get_subscription

router = APIRouter(
    tags=["Analytics"]
)

ANALYTICS_COLLECTION_NAME = "dauth_analytics"

@router.get("/analytics/{apikey}")
async def get_project_analytics(
    apikey: str, 
    month: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    user_email: str = Depends(verify_user)
):
    try:
        # If no custom range and no specific month, default to current month
        if not month and not start_date and not end_date:
            month = datetime.utcnow().strftime('%Y-%m')
            
        months_to_fetch = []
        
        if start_date and end_date:
            # Custom date range - compute all months spanned
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            curr = start_dt
            while curr <= end_dt:
                months_to_fetch.append(curr.strftime('%Y-%m'))
                curr += relativedelta(months=1)
        elif month:
            # Only one specific month requested
            months_to_fetch.append(month)
        else:
            # "Overall" implies fetching everything, but for simplicity we fetch the last 12 months if no month is provided
            # Wait, the frontend sends empty string for overall. We will handle this by returning all records for this apikey.
            months_to_fetch = None # special flag for 'all'
            
        query = {"_id": {"$regex": f"^{apikey}_"}} if months_to_fetch is None else {"_id": {"$in": [f"{apikey}_{m}" for m in months_to_fetch]}}
        cursor = db[ANALYTICS_COLLECTION_NAME].find(query)
        
        aggregated = {
            "total_requests": 0,
            "sms_otp_count": 0,
            "methods": {},
            "daily": {}
        }
        
        async for doc in cursor:
            if start_date and end_date:
                for date_key, daily_data in doc.get("daily", {}).items():
                    if start_date <= date_key <= end_date:
                        aggregated["daily"][date_key] = daily_data
                        aggregated["total_requests"] += daily_data.get("total_requests", 0)
                        aggregated["sms_otp_count"] += daily_data.get("sms_otp_count", 0)
                        for method, count in daily_data.get("methods", {}).items():
                            aggregated["methods"][method] = aggregated["methods"].get(method, 0) + count
            else:
                aggregated["total_requests"] += doc.get("total_requests", 0)
                aggregated["sms_otp_count"] += doc.get("sms_otp_count", 0)
                for method, count in doc.get("methods", {}).items():
                    aggregated["methods"][method] = aggregated["methods"].get(method, 0) + count
                for date_key, daily_data in doc.get("daily", {}).items():
                    aggregated["daily"][date_key] = daily_data

        subscription = await get_subscription(user_email)
        plan_name = subscription.get("plan", "Free") if subscription else "Free"
        
        quotas = {
            "Free": 2100,
            "Community": 2100,
            "Growth": 13500,
            "Scale": 40500,
            "Enterprise": "Unlimited"
        }
        aggregated["auth_quota"] = quotas.get(plan_name, 2100)
        
        return aggregated
        
    except Exception as e:
        ic(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics data")

@router.get("/analytics/{apikey}/logs")
async def get_audit_logs(
    apikey: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    identifier: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    user_email: str = Depends(verify_user)
):
    try:
        query = {"apikey": apikey}
        if identifier and identifier.strip():
            query["identifier"] = {"$regex": identifier.strip(), "$options": "i"}
        if method and method != "ALL":
            query["method"] = method
        if event_type and event_type != "ALL":
            query["event_type"] = event_type

        if start_date and end_date:
            try:
                start_ts = datetime.strptime(start_date, '%Y-%m-%d').timestamp()
                end_ts = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S').timestamp()
                query["timestamp"] = {"$gte": start_ts, "$lte": end_ts}
            except Exception:
                pass
        elif month and month != 'overall':
            try:
                start_dt = datetime.strptime(f"{month}-01", '%Y-%m-%d')
                end_dt = start_dt + relativedelta(months=1) - relativedelta(seconds=1)
                query["timestamp"] = {"$gte": start_dt.timestamp(), "$lte": end_dt.timestamp()}
            except Exception:
                pass
            
        skip = (page - 1) * limit
        cursor = db[AUDIT_LOGS_COLLECTION_NAME].find(query).sort("timestamp", -1).skip(skip).limit(limit)
        logs = []
        async for doc in cursor:
            doc.pop("_id", None)
            logs.append(doc)
            
        has_more = len(logs) == limit
        
        # Calculate IP abuse & User OTP summary when page == 1
        ip_abuse = []
        user_otp_abuse = []
        if page == 1:
            ip_counts = {}
            user_otp_counts = {}
            ip_query = {"apikey": apikey}
            if "timestamp" in query:
                ip_query["timestamp"] = query["timestamp"]
            ip_cursor = db[AUDIT_LOGS_COLLECTION_NAME].find(ip_query)
            async for doc in ip_cursor:
                ev = doc.get("event_type", "")
                met = doc.get("method", "")
                cnt = doc.get("count", 1)
                if "OTP" in ev or "otp" in met:
                    ip = doc.get("ip_address", "unknown")
                    ident = doc.get("identifier", "unknown")
                    ip_counts[ip] = ip_counts.get(ip, 0) + cnt
                    user_otp_counts[ident] = user_otp_counts.get(ident, 0) + cnt
            ip_abuse = [{"ip": ip, "count": count} for ip, count in ip_counts.items()]
            user_otp_abuse = [{"identifier": ident, "count": count} for ident, count in user_otp_counts.items()]

        return {
            "logs": logs,
            "has_more": has_more,
            "page": page,
            "ip_abuse": ip_abuse,
            "user_otp_abuse": user_otp_abuse
        }
    except Exception as e:
        ic(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")

@router.get("/analytics/{apikey}/otp-breakdown")
async def get_otp_breakdown(
    apikey: str,
    by: str = Query("ip", pattern="^(ip|user)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    user_email: str = Depends(verify_user)
):
    try:
        match_field = "ip_address" if by == "ip" else "identifier"
        
        match_stage = {
            "apikey": apikey,
            "$or": [
                {"event_type": {"$regex": "OTP", "$options": "i"}},
                {"method": {"$regex": "otp", "$options": "i"}}
            ]
        }
        
        if search and search.strip():
            match_stage[match_field] = {"$regex": search.strip(), "$options": "i"}

        if start_date and end_date:
            try:
                start_ts = datetime.strptime(start_date, '%Y-%m-%d').timestamp()
                end_ts = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S').timestamp()
                match_stage["timestamp"] = {"$gte": start_ts, "$lte": end_ts}
            except Exception:
                pass
        elif month and month != 'overall':
            try:
                start_dt = datetime.strptime(f"{month}-01", '%Y-%m-%d')
                end_dt = start_dt + relativedelta(months=1) - relativedelta(seconds=1)
                match_stage["timestamp"] = {"$gte": start_dt.timestamp(), "$lte": end_dt.timestamp()}
            except Exception:
                pass
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": f"${match_field}",
                "count": {"$sum": {"$ifNull": ["$count", 1]}}
            }},
            {"$sort": {"count": -1}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit}
        ]
        
        cursor = db[AUDIT_LOGS_COLLECTION_NAME].aggregate(pipeline)
        items = []
        async for doc in cursor:
            if doc["_id"]:
                items.append({
                    "key": doc["_id"],
                    "count": doc["count"]
                })
                
        has_more = len(items) == limit
        return {
            "items": items,
            "has_more": has_more,
            "page": page,
            "by": by
        }
    except Exception as e:
        ic(f"Error fetching OTP breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch OTP breakdown")



