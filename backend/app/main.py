from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.ranking import router as ranking_router
from app.api.routes.decision import router as decision_router
from app.api.routes.evidence import router as evidence_router

from app.api.routes.decision_create import router as decision_create_router
from app.api.routes.decision_read import router as decision_read_router
from app.api.routes.evidence_create import router as evidence_create_router
from app.api.routes.incident_create import router as incident_create_router
from app.api.routes.incident_read import router as incident_read_router
from app.api.routes.system_read import router as system_read_router

from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Decision-Aware Evidence Orchestration for One Health",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Existing Sang intelligence routes
app.include_router(evidence_router)
app.include_router(ranking_router)
app.include_router(decision_router)

# Upstream foundation routes
app.include_router(incident_read_router)
app.include_router(incident_create_router)
app.include_router(evidence_create_router)
app.include_router(decision_create_router)
app.include_router(decision_read_router)
app.include_router(system_read_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "incident_example": "/incidents/8f03fdce-cc4e-4fc1-a90b-15b2122e68b8",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aquapass-api",
    }