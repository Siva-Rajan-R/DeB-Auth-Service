import os
from motor.motor_asyncio import AsyncIOMotorClient
from configs.settings import settings

MONGODB_URI = settings.MONGODB_URI
DB_NAME = settings.MONGODB_DB_NAME

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]
