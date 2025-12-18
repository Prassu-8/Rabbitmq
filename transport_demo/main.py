# main.py
from fastapi import FastAPI
from transport_demo.transport_request import router as request_router


app = FastAPI(debug=True)


# @app.get("/")
# def read_root():
#     return {"message":"Hello World"}
app.include_router(request_router)
