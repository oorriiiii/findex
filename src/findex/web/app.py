import time
import uuid
import logging
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Query, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from findex.index import Index
from findex.search import SearchEngine

logger = logging.getLogger("findex.web")

# Глобальний стан для індексу (завантажується один раз через lifespan)
app_state = {
    "index": None,
    "engine": None,
    "index_path": Path("index.bin")
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: завантаження індексу
    path = app_state["index_path"]
    if path.exists():
        try:
            idx = Index.load(path)
            app_state["index"] = idx
            app_state["engine"] = SearchEngine(idx)
            logger.info(f"Індекс успішно завантажено з {path}")
        except Exception as e:
            logger.error(f"Помилка завантаження індексу: {e}")
    yield
    # Shutdown: очищення
    app_state["index"] = None
    app_state["engine"] = None


app = FastAPI(title="Findex Web API", version="0.7.0", lifespan=lifespan)

# Шаблони
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


# Pydantic моделі на межі (контракти)
class SearchResultItem(BaseModel):
    doc_id: int
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    results: List[SearchResultItem]


class HealthResponse(BaseModel):
    status: str
    index_loaded: bool


# Middleware для логування несподіваних винятків з requestId
@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.exception(f"[{request_id}] Необроблений виняток під час запиту {request.url}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "request_id": request_id}
        )


def get_engine():
    engine = app_state.get("engine")
    if not engine:
        raise HTTPException(status_code=503, detail="Index not loaded")
    return engine


@app.get("/health", response_model=HealthResponse)
def health_check():
    loaded = app_state.get("engine") is not None
    if not loaded:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "index_loaded": False})
    return {"status": "healthy", "index_loaded": True}


@app.get("/stats")
def stats(engine: SearchEngine = Depends(get_engine)):
    idx = engine.index
    return {
        "num_docs": len(idx),
        "vocab_size": len(idx.vocabulary) if hasattr(idx, "vocabulary") else 0
    }


# Використовуємо async def, щоб не блокувати цикл подій (non-blocking)
@app.get("/search", response_model=SearchResponse)
async def search(
        q: str = Query(..., min_length=1),
        k: int = Query(5, ge=1, le=50),
        scorer: str = Query("bm25", pattern="^(tfidf|bm25)$"),
        page: int = Query(1, ge=1),
        engine: SearchEngine = Depends(get_engine)
):
    try:
        # Виконуємо пошук із передачею скрорера напряму
        raw_results = engine.search(q, k=k * page, scorer=scorer)

        # Посторінкова пагінація
        start = (page - 1) * k
        end = start + k
        page_results = raw_results[start:end]

        items = [
            SearchResultItem(
                doc_id=r.doc_id,
                title=getattr(r, "title", f"Document {r.doc_id}"),
                snippet=getattr(r, "snippet", ""),
                score=r.score
            )
            for r in page_results
        ]

        return SearchResponse(
            query=q,
            total=len(raw_results),
            page=page,
            results=items
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/docs/{doc_id}")
def get_document(doc_id: int, engine: SearchEngine = Depends(get_engine)):
    idx = engine.index
    if doc_id not in idx:
        raise HTTPException(status_code=404, detail="Document not found")
    doc_data = idx[doc_id]
    return {"doc_id": doc_id, "content": doc_data}


@app.get("/", response_class=HTMLResponse)
async def index_page(
        request: Request,
        q: Optional[str] = None,
        scorer: str = "bm25",
        engine: Optional[SearchEngine] = Depends(get_engine)
):
    results = None
    total = 0
    if q and engine:
        try:
            raw_results = engine.search(q, k=10, scorer=scorer)
            results = [
                SearchResultItem(
                    doc_id=r.doc_id,
                    title=getattr(r, "title", f"Document {r.doc_id}"),
                    snippet=getattr(r, "snippet", "Без сніпета"),
                    score=r.score
                )
                for r in raw_results
            ]
            total = len(raw_results)
        except Exception:
            results = []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": q,
        "scorer": scorer,
        "results": results,
        "total": total
    })