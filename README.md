# Speller

[![GitHub](https://img.shields.io/badge/GitHub-StoneLabs%2FSpeller-24292f?logo=github&logoColor=white)](https://github.com/StoneLabs/Speller/)

Local AI grammar checker for authors. Paste from Word or LibreOffice, review paragraph by paragraph with aligned marginalia — all on your own hardware.

**Repository:** [github.com/StoneLabs/Speller](https://github.com/StoneLabs/Speller/)

## Features

- Rich-text editor — **bold**, *italic*, and underline survive paste and are sent to the model
- Two-phase workflow: write freely, then freeze into a read-only review layout
- Diff-based underlines (no unreliable character indices from the model)
- Per-paragraph toggle: original with marks ↔ AI-corrected text
- Clean paragraphs fade back so you can focus on flagged ones
- Works with any OpenAI-compatible local server (LM Studio, vLLM, etc.)

## Quick start

```bash
# terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# terminal 2 — frontend
cd frontend
npm install && npm run dev
```

Or run both with `./dev.sh`, then open http://localhost:5173

## Defaults

| Setting | Value |
|---------|-------|
| API | `http://lab-gpu2:1234` |
| Model | `qwen/qwen3.6-27b` |
| Context | 2 paragraphs before/after |

Use **Settings → Test connection** before your first review.

## Strictness

1. **Strict** — typos and clear grammar errors only  
2. **Balanced** — above + minor style fixes  
3. **Editor** — thorough editing suggestions  

## Stack

- **Backend:** Python, FastAPI  
- **Frontend:** Vue 3, Vite  

## License

See the [GitHub repository](https://github.com/StoneLabs/Speller/) for license details.
