from fastapi import FastAPI,Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from api.routers import deb_user_routes,auth_routes
from api.routers.auth_providers_routes import otp_auth,google_auth,github_auth,facebook_auth
from operations.fb_operations.users_crud import create_debuggers_cred,ic
from starlette.middleware.cors import CORSMiddleware
from exceptions import session_exp
import sys,os
from dotenv import load_dotenv
load_dotenv()

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

# adding custom exceptions
app.add_exception_handler(session_exp.SessionExpired,session_exp.session_exp_handler)

origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DeB Users Routes
app.include_router(deb_user_routes.router)


# Authentication Acess Route
app.include_router(auth_routes.router)


# Authentication Methods Routes
app.include_router(otp_auth.router)
app.include_router(google_auth.router)
app.include_router(github_auth.router)
app.include_router(facebook_auth.router)


template=Jinja2Templates("templates")
@app.get("/")
def root(request:Request):
    print({"message": "Welcome to DeB Users Authentication Service","Headers":request.cookies})
    return RedirectResponse(url=os.getenv("FRONTEND_URL"),status_code=302)
    # retu rn {"message": "Welcome to DeB Users Authentication Service","Headers":request.cookies}