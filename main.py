from fastapi import FastAPI
from api.routers import user_crud
from api.routers.authentication_crud import otp_auth,google_auth,github_auth,facebook_auth
from starlette.middleware.cors import CORSMiddleware


app=FastAPI()
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