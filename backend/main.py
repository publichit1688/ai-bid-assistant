from fastapi import FastAPI

app = FastAPI(
    title="AI Bid Assistant",
    version="0.1.0"
)

@app.get("/")
def root():
    return {"message": "Hello AI Bid Assistant"}