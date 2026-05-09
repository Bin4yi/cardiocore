# OWNER: Binula
# DAY:   3
# PURPOSE: SHARP context middleware for Prompt Opinion integration
#
# Prompt Opinion sends patient context via HTTP headers:
#   X-FHIR-Server-URL   â€” URL of the FHIR server for this patient
#   X-FHIR-Access-Token â€” Bearer token for FHIR server access
#   X-Patient-Id        â€” Patient identifier
#
# This middleware extracts those headers and makes them available
# to all request handlers via get_sharp_context().
#
# Usage in a FastAPI endpoint:
#   from mcp_server.sharp_context import get_sharp_context
#   ctx = get_sharp_context()
#   if ctx.has_fhir:
#       # fetch patient data from ctx.fhir_server_url

from contextvars import ContextVar
from dataclasses import dataclass
from fastapi import Request

@dataclass
class SHARPContext:
    fhir_server_url:   str = ''
    fhir_access_token: str = ''
    patient_id:        str = ''
    @property
    def has_fhir(self): return bool(self.fhir_server_url and self.fhir_access_token)

_ctx: ContextVar[SHARPContext] = ContextVar('sharp', default=SHARPContext())

async def sharp_middleware(request: Request, call_next):
    ctx = SHARPContext(
        fhir_server_url   = request.headers.get('X-FHIR-Server-URL',''),
        fhir_access_token = request.headers.get('X-FHIR-Access-Token',''),
        patient_id        = request.headers.get('X-Patient-Id',''),
    )
    tok = _ctx.set(ctx)
    try:    response = await call_next(request)
    finally: _ctx.reset(tok)
    return response

def get_sharp_context() -> SHARPContext:
    return _ctx.get()


