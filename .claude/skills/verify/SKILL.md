---
name: verify
description: Build, launch, and drive BacktestLab locally to verify changes end-to-end (backend API + React frontend + Playwright screenshots).
---

# Verify BacktestLab

## Launch (in order)

1. **Docker Postgres** (engine must be up first):
   ```powershell
   # If docker info fails, start Docker Desktop and wait ~60s:
   Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
   docker compose up -d   # from repo root; container: backtestlab-db
   ```
2. **Backend** (run in background):
   ```powershell
   cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Ready when `GET http://127.0.0.1:8000/health` → `{"status":"ok","database":"up"}`.
3. **Frontend** (run in background):
   ```powershell
   cd frontend; npm run dev
   ```
   Serves at `http://localhost:5173` (IPv6 — probe `localhost`, not `127.0.0.1`).

## Drive (Playwright)

No Playwright in deps. `npm i -D playwright-core` in `frontend/`, launch with
`chromium.launch({ channel: "chrome" })` (system Chrome). **Uninstall and
`git checkout -- frontend/package-lock.json` afterwards** — npm rewrites the
lockfile wholesale.

Scripts run from outside `frontend/` need
`createRequire("D:/sahdev works/BB/frontend/package.json")` to resolve the package.

Flow selectors:
- Landing → lab: `button.hero-btn`
- Dev sign-in: fill `getByPlaceholder("you@example.com")`, click "Sign in (dev)"
  (token `dev:<email>`; `tester@backtestlab.dev` is PRO in the local DB)
- Run: button "Run backtest"; results ready when a `canvas` appears (+1s paint)
- **Save uses `window.prompt`** — headless auto-dismisses it and save silently
  cancels. Register `page.on("dialog", d => d.accept("name"))` first.
- Delete uses `window.confirm` — same trap.

## API probes

`-H "Authorization: Bearer dev:tester@backtestlab.dev"` against
`http://127.0.0.1:8000` (`/me`, `/backtests`, `/strategies`). Clean up any
rows you create (`DELETE /backtests/{id}`).

## Gotchas

- PowerShell CWD persists between tool calls — `Set-Location` relative paths
  compound; use absolute paths.
- CI equivalents: `npx tsc -b --noEmit`, `npm test -- --run`, `npm run build`
  (all in `frontend/`); backend: `.venv` pytest. These are NOT verification.
