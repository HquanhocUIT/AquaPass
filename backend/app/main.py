from fastapi import FastAPI

from app.api.routes.ranking import router as ranking_router
from app.api.routes.decision import router as decision_router
from app.api.routes.evidence import router as evidence_router


app = FastAPI(
    title="AquaPass API",
    version="0.1.0",
    description="Decision-Aware Evidence Orchestration for One Health",
)

app.include_router(evidence_router)

app.include_router(ranking_router)
app.include_router(decision_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "aquapass-api",
    }