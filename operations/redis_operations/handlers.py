from configs.redis_config import redis
import json
from icecream import ic


async def redis_set(key:str,value,exp:int=None):
    try:
        dumbed_value=json.dumps(value)
        await redis.set(name=key,value=dumbed_value,ex=exp)
        ic("Redis : stored successfully",dumbed_value)
        return "Redis : stored successfully"
    except Exception as e:
        ic(f"Error : Redis storing {e}")

async def redis_unlink(*keys:str):
    try:
        await redis.unlink(*keys)
        ic("Redis : Successfully Unlinked")
        return "Redis : Successfully Unlinked"
    except Exception as e:
        ic(f"Error : Redis unlinking {e}")

async def redis_get(key:str):
    try:
        data=await redis.get(key)
        if data!=None:
            data=json.loads(data)
        
        ic(data)
        return data
    except Exception as e:
        ic(f"Error : Redis Get {e}")

async def redis_curttl(key:str):
    try:
        curttl=await redis.ttl(name=key)
        ic(curttl)
        return curttl
    except Exception as e:
        ic(f"Error : Redis Curttl {e}")
    
    