"""
Model Inference API Service
Fulfills the OpenAPI 3.0 contract for ML model inference and health checking.
"""
from fastapi import FastAPI, Request, Response, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="Model Inference API",
    version="1.0.0",
    description="A simple API for text classification inference.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request schema enforcing required non-empty text string
class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Input text to classify")

# Response schema matching OpenAPI contract
class PredictResponse(BaseModel):
    label: str
    score: float

class HealthResponse(BaseModel):
    status: str

# Positive and negative lexical sets for stub sentiment classification
POSITIVE_KEYWORDS = {
    "good", "great", "excellent", "happy", "love", "positive",
    "awesome", "fantastic", "best", "amazing", "wonderful", "satisfied"
}
NEGATIVE_KEYWORDS = {
    "bad", "poor", "terrible", "sad", "hate", "negative",
    "awful", "horrible", "worst", "broken", "slow", "complaint", "unsatisfied"
}

@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.head("/health", include_in_schema=False)
def health_check():
    """Health check endpoint used by Docker and proxy routing."""
    return {"status": "ok"}

@app.post("/v1/predict", response_model=PredictResponse, status_code=status.HTTP_200_OK, tags=["Inference"])
def predict(payload: PredictRequest):
    """
    Model inference endpoint.
    Extracts text, performs stub classification inference, and returns predicted label and score.
    """
    text_lower = payload.text.lower()
    
    pos_score = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg_score = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    
    if pos_score > neg_score:
        label = "positive"
        score = 0.95
    elif neg_score > pos_score:
        label = "negative"
        score = 0.88
    else:
        label = "neutral"
        score = 0.70
        
    return PredictResponse(label=label, score=float(score))

@app.head("/v1/predict", include_in_schema=False)
def predict_head():
    """Support HEAD requests for curl -I checks."""
    return Response(status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
