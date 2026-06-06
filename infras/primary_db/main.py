from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession,async_sessionmaker
from sqlalchemy.orm import declarative_base
from icecream import ic


BASE=declarative_base()

ENGINE=create_async_engine(url="")


AsyncSessionLocal=async_sessionmaker(bind=ENGINE)


async def get_async_db_session():
    Session=AsyncSessionLocal()
    try:
        yield Session
    except:
        ic("Somethig went wrong while gtttign the session")
    finally:
        Session.close()


async def init_db():
    async with AsyncSessionLocal() as session:
        await session.run_sync(BASE.metadata.create_all)
        await session.commit()
    


