# Speller

Local AI grammar checker for authors. One manuscript editor on the left, marginalia on the right.

## Run

```bash
# terminal 1
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# terminal 2
cd frontend
npm run dev
```

Or `./dev.sh` — then open http://localhost:5173

## Defaults

| Setting | Value |
|---------|-------|
| API | `http://lab-gpu2:1234` |
| Model | `qwen/qwen3.6-27b` |
| Context | 2 lines before/after |

Use **Settings → Test connection** to verify the model before reviewing.

## Usage

1. Paste from Word or LibreOffice into the manuscript pane (bold/italic preserved)
2. Click **Review manuscript**
3. Issues appear as wavy underlines; marginalia aligns to each line
