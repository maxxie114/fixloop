import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI()

BUG_STATE = {"enabled": False}

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/catalog")
async def catalog():
    return {
        "products": [
            {"id": "1", "name": "Widget A", "price": 19.99, "in_stock": True},
            {"id": "2", "name": "Widget B", "price": 29.99, "in_stock": True},
            {"id": "3", "name": "Widget C", "price": 39.99, "in_stock": False},
        ]
    }

@app.post("/checkout")
async def checkout(request: Request):
    if BUG_STATE["enabled"]:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "message": "Checkout service unavailable"}
        )
    
    body = await request.json()
    return {
        "order_id": "ORD-" + str(int(time.time())),
        "status": "confirmed",
        "items": body.get("items", []),
        "total": sum(item.get("price", 0) for item in body.get("items", []))
    }

@app.post("/admin/bug")
async def toggle_bug():
    BUG_STATE["enabled"] = not BUG_STATE["enabled"]
    return {"enabled": BUG_STATE["enabled"]}

@app.get("/admin/bug")
async def get_bug_state():
    return {"enabled": BUG_STATE["enabled"]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DEMO_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
