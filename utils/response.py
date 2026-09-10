from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(message: str = "success", data=None):
    content = {
        "code": 200,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(content))


def error_response(message: str = "error", code: int = 400, data=None):
    content = {
        "code": code,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(content), status_code=code)
