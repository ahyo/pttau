# Company Profile — FastAPI + Bootstrap + MySQL (ID/EN/AR)

## Quickstart (Local)
```bash
python -m venv .venv && source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Deploy on cPanel (shared hosting)
- Use **Setup Python App** (Passenger)
- App dir: `~/company-profile`
- Startup file: `passenger_wsgi.py`, Entry point: `app`
- Install from `requirements.txt`
- Set env from `.env`
