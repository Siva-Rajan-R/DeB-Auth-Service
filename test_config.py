import asyncio
import json
from operations.redis_operations.handlers import redis_get

async def run():
    req_id = 'e8f676a3-f7f2-53c3-83d5-15635d6ae61a'
    v = await redis_get(req_id)
    if v:
        print(json.dumps(v['config'], indent=2))
    else:
        print('not found')

if __name__ == '__main__':
    asyncio.run(run())
