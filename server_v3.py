"""
server_v3.py
------------
Minimal server to preview the v3 dashboard design.
Run:  python server_v3.py          (port 8001)
  or: uvicorn server_v3:app --port 8001 --reload
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="AgentGuard v3 Preview", version="3.0.0")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def root():
    html_file = STATIC_DIR / "page_dashboard_v3.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>page_dashboard_v3.html not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_v3:app", host="0.0.0.0", port=8001, reload=True)
