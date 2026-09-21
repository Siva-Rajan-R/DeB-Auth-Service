from fastapi import FastAPI,Request,routing
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from api.routers import deb_user_routes,auth_routes, billing_routes, analytics_routes
from api.routers.auth_providers_routes import otp_auth,google_auth,github_auth,facebook_auth,password_auth,forgot_password,two_factor_auth

from api.routers import admin_routes
from operations.mongo_operations.users_crud import create_debuggers_cred,ic
from starlette.middleware.cors import CORSMiddleware
from middlewares.invalid_route_middleware import InvalidRouteHandleMiddleware
from exceptions import session_exp
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
from dotenv import load_dotenv
load_dotenv()


from core.logger import setup_logging, logger, ColoredRequestLoggingMiddleware

setup_logging()

if sys.platform!='win32':
    import uvloop,asyncio
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from contextlib import asynccontextmanager
import asyncio
from operations.mongo_operations.cron_jobs import check_and_notify_subscriptions

async def cron_loop():
    while True:
        await check_and_notify_subscriptions()
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app : FastAPI):
    try:
        cred_res = await create_debuggers_cred(os.getenv("REDIRECT_BASEURL"))
        logger.success(f"DAuth credentials initialized: {cred_res}")
    except Exception as e:
        logger.error(f"Error initializing credentials: {e}")
    
    cron_task = asyncio.create_task(cron_loop())
    logger.info("DAuth Authentication Service started successfully.")
    yield
    cron_task.cancel()
    logger.info("Server stopped...")

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
app.include_router(billing_routes.router)
app.include_router(analytics_routes.router)


template=Jinja2Templates("templates")
@app.get("/")
def root(request:Request):
    print({"message": "Welcome to DeB Users Authentication Service","Cookies":request.cookies})
    # return RedirectResponse(url=os.getenv("FRONTEND_URL"),status_code=302)
    return {"message": "Welcome to DeB Users Authentication Service","Cookies":request.cookies}

# adding custom exceptions
app.add_exception_handler(session_exp.SessionExpired,session_exp.session_exp_handler)

frontend_origins = ["https://authdebuggers.vercel.app","http://localhost:5173","https://dauth.debuggerstechnologies.com"]


# middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(InvalidRouteHandleMiddleware, routes=[r.path for r in app.routes if hasattr(r, 'path')])

# Colored Request Logging Middleware (Outermost - logs 100% of all requests/responses)
app.add_middleware(ColoredRequestLoggingMiddleware)

