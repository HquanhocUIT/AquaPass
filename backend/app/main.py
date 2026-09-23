from fastapi import FastAPI

app = FastAPI(
    title="AquaPass API",
    version="0.1.0",
    description="Decision-Aware Evidence Orchestration for One Health",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "aquapass-api",
    }