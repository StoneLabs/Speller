import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from checker import check_line, list_models_with_meta, test_connection
from prompts import STRICTNESS

app = FastAPI(title="Speller", version="1.0.0")

DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AiConfig(BaseModel):
    api_base: str = ""
    model: str = ""
    api_key: str = ""


class CheckLineRequest(AiConfig):
    target_line: str
    line_number: int = Field(ge=1)
    context_before: list[str] = Field(default_factory=list)
    context_after: list[str] = Field(default_factory=list)
    strictness: int = Field(default=2, ge=1, le=3)


class CheckDocumentRequest(AiConfig):
    lines: list[str]
    context_range: int = Field(default=2, ge=0, le=10)
    strictness: int = Field(default=2, ge=1, le=3)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/defaults")
async def defaults():
    return {
        "api_base": os.environ.get("SPELLER_LLM_API_BASE", ""),
    }


@app.get("/api/strictness-levels")
async def strictness_levels():
    return [
        {"level": k, "name": v["name"], "description": v["description"]}
        for k, v in sorted(STRICTNESS.items())
    ]


@app.post("/api/models")
async def api_models(req: AiConfig):
    try:
        pull_model = os.environ.get("SPELLER_OLLAMA_PULL_MODEL", "").strip() or None
        return await list_models_with_meta(
            api_base=req.api_base,
            api_key=req.api_key,
            pull_model=pull_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/test-connection")
async def api_test_connection(req: AiConfig):
    try:
        return await test_connection(
            api_base=req.api_base,
            model=req.model,
            api_key=req.api_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/check-line")
async def api_check_line(req: CheckLineRequest):
    try:
        return await check_line(
            target_line=req.target_line,
            line_number=req.line_number,
            context_before=req.context_before,
            context_after=req.context_after,
            strictness=req.strictness,
            api_base=req.api_base,
            model=req.model,
            api_key=req.api_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/check-document")
async def api_check_document(req: CheckDocumentRequest):
    results = []
    n = len(req.lines)
    for i, line in enumerate(req.lines):
        before = req.lines[max(0, i - req.context_range) : i]
        after = req.lines[i + 1 : min(n, i + 1 + req.context_range)]
        try:
            result = await check_line(
                target_line=line,
                line_number=i + 1,
                context_before=before,
                context_after=after,
                strictness=req.strictness,
                api_base=req.api_base,
                model=req.model,
                api_key=req.api_key,
            )
        except Exception as exc:
            result = {
                "line_number": i + 1,
                "original": line,
                "corrected": line,
                "issues": [],
                "notes": [],
                "hint": None,
                "has_issues": False,
                "error": str(exc),
            }
        results.append(result)
    return {"results": results}


if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
