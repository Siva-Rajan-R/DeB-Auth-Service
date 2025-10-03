from fastapi import FastAPI,Request
from api.routers import user_crud
from api.routers.authentication_crud import otp_auth,google_auth,github_auth,facebook_auth
from fb_database.operations.users_crud import create_debuggers_cred,ic
from starlette.middleware.cors import CORSMiddleware
import sys

if sys.platform!='win32':
    import uvloop,asyncio
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def lifespan(app : FastAPI):
    try:
        ic(create_debuggers_cred("http://127.0.0.1:8000/"))
        yield
    except Exception as e:
        ic(e)
    finally:
        ic("Server stopped...")

app=FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "https://xr84gnz1-8000.inc1.devtunnels.ms"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DeB Users Authentication Service
app.include_router(user_crud.router)

# Client Authentication services
app.include_router(otp_auth.router)
app.include_router(google_auth.router)
app.include_router(github_auth.router)
app.include_router(facebook_auth.router)

@app.get("/")
def root(request:Request):
    print({"message": "Welcome to DeB Users Authentication Service","Headers":request.cookies})
    return {"message": "Welcome to DeB Users Authentication Service","Headers":request.cookies}