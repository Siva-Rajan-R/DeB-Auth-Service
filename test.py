from fastapi import FastAPI,Request

app=FastAPI()

@app.get("/login/callback")
def sample(req:Request):
    return req.query_params

    
    

