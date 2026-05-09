# OWNER: Binula
# DAY:   3
# PURPOSE: Consistent JSON error responses for all MCP endpoints
#
# Ensures all errors return: {error: str, code: int}
# so Prompt Opinion agents can parse them reliably

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code,
        content={'error':exc.detail,'code':exc.status_code})

async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500,
        content={'error':'Internal server error','detail':str(exc),'code':500})
