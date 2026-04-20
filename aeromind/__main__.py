"""python -m aeromind.api.main — run API (requires uvicorn)."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("aeromind.api.main:app", host="0.0.0.0", port=8080, reload=False)
