# Cuemath Build Challenge — Flashcard Engine
This project implements **Problem 1: The Flashcard Engine** as a complete, deployable product.
Users upload a PDF chapter/notes file, get a smart flashcard deck, and review with spaced repetition plus progress tracking.

## What this submission includes
- PDF ingestion (`.pdf` upload) with text extraction
- Automatic flashcard generation from uploaded material
- Spaced repetition scheduler (SM-2 style)
- Review flow with answer reveal and difficulty scoring
- Progress dashboard (due cards, mastery, accuracy, total reviews)
- Search/revisit view for previously generated cards
- SQLite persistence for decks, cards, and review history
- Deployment-ready setup for Render/free hosting

## Tech stack
- Backend: Flask + SQLite
- Frontend: HTML/CSS/Vanilla JavaScript
- PDF parsing: `pypdf`
- Production server: `gunicorn`
- Tests: `pytest`

## Project structure
- `run.py` — application entrypoint
- `app/routes.py` — API and page routes
- `app/flashcard_engine.py` — flashcard generation logic
- `app/srs.py` — spaced repetition scheduling algorithm
- `app/pdf_ingestion.py` — PDF text extraction
- `app/db.py` — SQLite schema and connection utilities
- `app/templates/index.html` — UI layout
- `app/static/styles.css` — styling
- `app/static/app.js` — frontend behavior
- `tests/test_srs.py` — scheduler tests

## Local setup
1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Run the app:
   `python run.py`
4. Open:
   `http://localhost:5000`

## How to use
1. Upload a PDF and optionally set deck title/card count.
2. Select the generated deck.
3. Review due cards:
   - **Again** (1)
   - **Hard** (3)
   - **Good** (4)
   - **Easy** (5)
4. Track progress and search cards anytime.

## Spaced repetition logic
The scheduler uses an SM-2-inspired update model:
- Low score (<3): reset repetitions, review tomorrow
- Higher scores: increase repetition streak and interval
- Ease factor adapts based on score and is bounded to avoid collapse

This keeps difficult cards recurring sooner while mastered cards get longer intervals.

## Deployment (Render)
### Option A: Blueprint (recommended)
1. Push this repo to GitHub.
2. In Render, create a new Blueprint and select this repo.
3. Render will detect `render.yaml` and provision the web service.
4. Set any additional environment variables if required.

### Option B: Manual web service
1. New Web Service -> connect GitHub repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn run:app`
4. Set environment variable:
   - `SECRET_KEY` = random long secret
5. Deploy and use the generated public URL.

## Security notes
- No hardcoded API keys or credentials
- Sensitive config comes from environment variables
- Inputs validated for file type/size and score ranges
- SQLite DB stored server-side (`instance/`)
