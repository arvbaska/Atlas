# ATLAS — Private Autonomous Trading Control Centre

## Iteration 1 (demo-only)

A responsive Next.js frontend + FastAPI backend + PostgreSQL database for a private trading dashboard. It includes **eight sections**: Overview, Strategies, Screener, Positions & Orders, Decision Centre, Backtesting, Risk Control, and Settings. Seeded samples are deterministic and clearly labelled; configuration changes persist and audit events are recorded.

**No brokerage integration, trading engine, live quote feed or order-submission route is implemented.** This version cannot trade. The example backtesting values are mock data; no actual backtests have run.

## Quick start with Docker Compose

1. Copy `.env.example` to `.env`.
2. Set a strong unique `PRIVATE_PASSWORD` and a randomly generated 32+-character `SESSION_SECRET`. Do not commit `.env`.
3. Run `docker compose up --build`.
4. Open `http://localhost:3000` and sign in with `PRIVATE_PASSWORD`.

`http://localhost:8000/docs` serves FastAPI documentation (data endpoints require a bearer session token). Both containers bind to localhost by default. Do not deploy publicly without TLS, hardening, production secrets management, stricter login rate-limiting, database migrations and monitoring.

## Local development without Docker

Backend:
```sh
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PRIVATE_PASSWORD='your-strong-password'
export SESSION_SECRET='your-unique-secret-of-at-least-32-characters'
# Optional: defaults to SQLite for rapid development; Docker uses PostgreSQL.
uvicorn app.main:app --reload
```

Frontend (separate terminal):
```sh
cd web
cp .env.example .env.local
npm install
npm run dev
```

## Delivered stages

1. **Foundation:** frontend/backend repositories, environment configuration, database bootstrapping and containers.
2. **Design system:** dark responsive sidebar, KPI cards, tables, charts, status treatments and private sign-in.
3. **Core portfolio:** persisted strategies, sample positions and orders, portfolio dashboard.
4. **Research & configuration:** screener, signal reasoning, demonstration backtesting workspace, editable risk settings.
5. **Security & audit:** bearer sessions, private endpoints, server-side validation, audit trail, fail-safe demo mode.
6. **Testing:** API tests and static compile/build checks (run commands below).
7. **Delivery:** documented startup, deployment boundaries and clear future integration seams.

## Security & product limitations

- Password-based access is for a private demo, not a production identity system; tokens remain in browser memory and expire after 8 hours.
- The risk policy is **configuration only** and does not actually protect trades because no execution service exists.
- All prices, positions, signals, P&L and performance are synthetic examples.
- Strategy allocations are globally capped at the illustrative $10,000 demo pool. Allocation updates and new drafts are audited. There is no automated decision-making service.
- Data tables intentionally model the core concepts but are not yet a full event-sourced brokerage ledger; reconciliation, actual fill handling, FX and market data ingestion belong in future iterations.
- No IBKR secrets are stored, and the web client never receives any brokerage credentials.
- For local deployment only. Broker integration and any live-order capability explicitly excluded.

## Checks

Backend: `cd api && pytest -q`
Frontend: `cd web && npm run lint && npm run build`

## Verification performed in this environment

Backend `pytest -q`: PASS (1 end-to-end API test).
Backend Python compilation: PASS.
Frontend dependency installation/build: NOT VERIFIED because npm dependency retrieval did not complete in the execution environment. Run `npm install && npm run lint && npm run build` locally before relying on the UI. Docker startup was not available here.
