from redis.asyncio.client import Redis
import os
from dotenv import load_dotenv
load_dotenv()

redis=Redis.from_url(url=os.getenv("REDIS_URL"),decode_responses=True)
