from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.tools.analyze_ecg import (
    router as ecg_router
)

# Future routers
# (keep placeholders for now)
try:
    from mcp_server.tools.estimate_ef import (
        router as ef_router
    )
except:
    ef_router = None

try:
    from mcp_server.tools.analyze_structure import (
        router as structure_router
    )
except:
    structure_router = None

try:
    from mcp_server.tools.risk_stratify import (
        router as risk_router
    )
except:
    risk_router = None

try:
    from mcp_server.tools.generate_report import (
        router as report_router
    )
except:
    report_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    from inference.gemma4_client import (
        get_client
    )

    print(
        "Checking Gemma multimodal system..."
    )

    if not get_client().healthy():

        print(
            "WARNING: Gemma API not reachable"
        )

    else:

        print(
            "Gemma ready:",
            get_client().model_id
        )

    print(
        "CardioCore MCP Server ready."
    )

    yield


app = FastAPI(
    title="CardioCore MCP Server",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register routers
app.include_router(ecg_router)

if ef_router:
    app.include_router(ef_router)

if structure_router:
    app.include_router(structure_router)

if risk_router:
    app.include_router(risk_router)

if report_router:
    app.include_router(report_router)


@app.get("/health")
def health():

    from inference.gemma4_client import (
        get_client
    )

    return {

        "status": "healthy",

        "vllm_ready": get_client().healthy(),

        "model": get_client().model_id
    }


@app.get("/mcp/tools")
def mcp_tools():

    return {

        "schema_version": "1.0",

        "name": "CardioCore",

        "tools": [

            {
                "name": "analyze_ecg_leads",
                "endpoint": "/tools/analyze_ecg_leads",
                "method": "POST"
            },

            {
                "name": "estimate_ejection_fraction",
                "endpoint": "/tools/estimate_ejection_fraction",
                "method": "POST"
            },

            {
                "name": "analyze_cardiac_structure",
                "endpoint": "/tools/analyze_cardiac_structure",
                "method": "POST"
            },

            {
                "name": "risk_stratify",
                "endpoint": "/tools/risk_stratify",
                "method": "POST"
            },

            {
                "name": "generate_cardiac_report",
                "endpoint": "/tools/generate_cardiac_report",
                "method": "POST"
            }
        ]
    }


@app.get("/.well-known/mcp")
def well_known():

    return {

        "mcp_tools_url": "/mcp/tools",

        "version": "1.0"
    }
