from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from fastapi.requests import Request


template=Jinja2Templates("templates")

class SessionExpired(Exception):
    def __init__(self, redirect_url:str,message:str="Session Expired Redirecting..."):
        self.message=message
        self.redirect_url=redirect_url
        super().__init__(self.message,self.redirect_url)

async def session_exp_handler(request:Request,error:SessionExpired):
    # return JSONResponse(
    #     content={"error":"vanakam Your session expired",'msg':error.message},
    #     status_code=401,
    # )

    return template.TemplateResponse("redirect.html",status_code=401,name="Session expired",context={"request":request,"redirect_url":error.redirect_url,'error_msg':error.message})