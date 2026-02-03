# Enterprise Standalone (ERP core)

Runs these modules together on a single FastAPI app + SQLite database:
- Inventory
- Sales
- Purchasing
- Accounting
- QMS
- MRP

## Run backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Health
- `GET /health`
- `GET /inventory/health`
- `GET /sales/health`
- `GET /purchasing/health`
- `GET /accounting/health`
- `GET /qms/health`
- `GET /mrp/health`

## Minimal CRUD included
- Inventory: create/list items
- Sales: create/list customers; create quotes/orders (with lines)
- Purchasing: create/list vendors; create purchase orders (with lines)
- Accounting: create/list GL accounts; create journals (with lines)
- QMS: create/list inspection plans; create inspections
- MRP: create/list work centers; create BOMs (with lines)


## WMS
- WMS demo endpoints:
  - /inventory/items, /inventory/locations, /inventory/balances
  - /docs/* (receipts, orders, counts)
  - /tasks/*, /waves/*, /exceptions/*, /counts/submissions
- ERP inventory endpoints are available under /erp/inventory/*

### Operator UI
```bash
cd frontend/operator-ui
npm install
npm run dev
```


## PostgreSQL
This build is configured for PostgreSQL by default.

Start Postgres:
```bash
docker compose up -d
```
Run backend (DATABASE_URL optional):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise'
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Module installer UI (frontend)
This build includes a simple admin UI to install/enable/disable modules.

Run it:
```bash
cd frontend/module-admin
npm install
npm run dev
```

Then open the UI (default port 5174) and use:
- Install (dependency-aware)
- Enable/Disable
- Seed (example: WMS default locations)

## Module gating (enabled/disabled)
All module routers are gated by the `sys_tenant_module` table:
- If a module is not enabled, its endpoints respond with **404** (it disappears).
- Use the Module Installer UI to install + enable required modules.

Recommended bootstrap order:
1) Install + enable `inventory`
2) Install + enable `sales`, `purchasing`, `accounting`, `qms`, `mrp`
3) Install + enable `wms`
4) (Optional) Seed WMS defaults: `wms → default_locations`

## Module upgrade
The UI includes an Upgrade button that bumps `installed_version` to the packaged `version`.
In production, this is where Alembic migrations would run.


## ERP Repo (composition)
This repo is the **ERP**: a single FastAPI backend + Postgres + packaged modules + installer UI.

### Run Postgres
```bash
docker compose up -d
```

### Run backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/enterprise'
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run module installer UI
```bash
cd frontend/module-admin
npm install
npm run dev
```

### Run ERP web shell
```bash
cd frontend/erp-web
npm install
npm run dev
```

### Alembic migrations (real upgrades)
Initialize DB to baseline (first run):
```bash
cd backend
alembic -c alembic.ini stamp 0001_baseline
```

Create a new migration after model changes:
```bash
cd backend
alembic -c alembic.ini revision --autogenerate -m "change"
alembic -c alembic.ini upgrade head
```

Module upgrade endpoint now runs:
- `alembic upgrade head`
so upgrades are **real**.

### Tenant isolation
Send header:
- `X-Tenant-Id: <tenant>`
Default tenant is `default`.

### MES FIFO -> WIP + genealogy
- `POST /mes/production-orders/{id}/issue-materials` issues FIFO from balances and writes `ISSUE_TO_WIP` txns.
- `POST /mes/production-orders/{id}/receive-fg` creates FG receipt txn and `inv_genealogy_link` rows.
