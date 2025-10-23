![Deploy CI/CD](https://github.com/ahyo/pttau/actions/workflows/deploy.yml/badge.svg)

# PT TAU — FastAPI + Bootstrap + MySQL (ID/EN/AR)

## Quickstart (Local)
```bash
python -m venv .venv && source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Database migrations (Alembic)

```bash
alembic upgrade head      # apply latest migrations
alembic revision -m "msg" # create a new migration after editing models
```

On a new environment that already has the schema, mark the baseline first:

```bash
alembic stamp 0001_baseline
```

## Deploy on cPanel (shared hosting)
- Use **Setup Python App** (Passenger)
- App dir: `~/company-profile`
- Startup file: `passenger_wsgi.py`, Entry point: `app`
- Install from `requirements.txt`
- Set env from `.env`
