from fastapi import FastAPI,Request
from fastapi.routing import APIRoute
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from exceptions.session_exp import SessionExpired
import time,os
from dotenv import load_dotenv
load_dotenv()

template=Jinja2Templates("templates")

class InvalidRouteHandleMiddleware(BaseHTTPMiddleware):
    def  __init__(self,app,routes):
        super().__init__(app)
        self.routes=routes

    async def dispatch(self, request, call_next):
        try:
            print(self.routes)
            rid=template.TemplateResponse("redirect.html",status_code=404,name="Page Not Found",context={"request":request,"redirect_url":os.getenv("FRONTEND_URL"),'error_msg':"Page Not Found Redirecting to DeB-Auth-Service..."})
            print("path params : ",request.path_params,"query params: ",request.query_params,'incoming path: ',request.url.path)
            # path=request.url.path.split('/')[0:-1]
            # print('/'.join(path))
            if os.getenv("CURRENT_ENVIRONMENT","production").lower()=="production" and request.method.lower()=="get" and request.url.path=="/users":
                return rid
            
            # if (request.url.path not in self.routes):
            #     return rid
            
            response:Response=await call_next(request)

            return response
        except SessionExpired:
            raise