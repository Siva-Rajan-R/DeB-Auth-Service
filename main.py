from fastapi import FastAPI,Request,routing
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from api.routers import deb_user_routes,auth_routes
from api.routers.auth_providers_routes import otp_auth,google_auth,github_auth,facebook_auth,password_auth,forgot_password,two_factor_auth

from api.routers import admin_routes
from operations.fb_operations.users_crud import create_debuggers_cred,ic
from starlette.middleware.cors import CORSMiddleware
from middlewares.invalid_route_middleware import InvalidRouteHandleMiddleware
from exceptions import session_exp
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
from dotenv import load_dotenv
load_dotenv()


if sys.platform!='win32':
    import uvloop,asyncio
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def lifespan(app : FastAPI):
    try:
        ic(create_debuggers_cred(os.getenv("REDIRECT_BASEURL")))
        yield
    except Exception as e:
        ic(e)
    finally:
        ic("Server stopped...")

docs_url='/docs'
redoc_url='/redoc'
openapi_url='/openapi.json'

if os.getenv("CURRENT_ENVIRONMENT",'production').lower()=="production":
    docs_url=None
    redoc_url=None
    openapi_url=None

app=FastAPI(lifespan=lifespan,docs_url=docs_url,redoc_url=redoc_url,openapi_url=openapi_url)


# routes

# DeB Users Routes
app.include_router(deb_user_routes.router)

# Authentication Acess Route
app.include_router(auth_routes.router)

# Authentication Methods Routes
app.include_router(otp_auth.router)
app.include_router(google_auth.router)
app.include_router(github_auth.router)
app.include_router(facebook_auth.router)
app.include_router(password_auth.router)
app.include_router(forgot_password.router)
app.include_router(two_factor_auth.router)


# Admin Routes
app.include_router(admin_routes.router)


template=Jinja2Templates("templates")
@app.get("/")
def root(request:Request):
    print({"message": "Welcome to DeB Users Authentication Service","Cookies":request.cookies})
    # return RedirectResponse(url=os.getenv("FRONTEND_URL"),status_code=302)
    return {"message": "Welcome to DeB Users Authentication Service","Cookies":request.cookies}

# adding custom exceptions
app.add_exception_handler(session_exp.SessionExpired,session_exp.session_exp_handler)

frontend_origins = ["https://authdebuggers.vercel.app","http://localhost:5173","https://dauth.debuggers.co.in"]


# middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(InvalidRouteHandleMiddleware, routes=[r.path for r in app.routes if hasattr(r, 'path')])
