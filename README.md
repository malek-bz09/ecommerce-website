# UNDERGROUND

React + Vite (with React Compiler) storefront, with a Python FastAPI backend in `backend/`.

## Run it

Start PostgreSQL first (needs Docker), then two terminals:

```sh
docker compose up -d   # PostgreSQL on localhost:5432 (user/password/db: shop)

# 1. Backend (needs uv: https://docs.astral.sh/uv/) — http://localhost:8000
pnpm api

# 2. Frontend — http://localhost:5173
pnpm install
pnpm dev
```

Vite forwards every `/api/...` request to the backend, so both must be running.
To point it at another backend: `API_URL=http://localhost:9000 pnpm dev`.
API docs (try requests in the browser): http://localhost:8000/docs

## How a sale works

Open an order in **Admin → Orders** to see its full details and move it along:

```
pending ──► confirmed ──► delivered
   │            │             │
   │            ├──► returned ◄┘   (items go back in stock)
   ▼            ▼
cancelled ◄─────┘                  (items go back in stock if it was confirmed)
```

- **Confirm sale** takes the items out of stock and adds the buyer to Customers.
- **Revenue** on the dashboard counts delivered orders only (cash on delivery).

## Products

Add, edit and delete products in **Admin → Products**, including uploading a photo
(saved in `backend/data/uploads/`). The shop loads products from the backend, so
changes show up straight away. Deleting hides a product but keeps it in old orders.

## Admin accounts

Sign in at **/admin**. There is no sign-up; accounts are created
on the server. On first run two accounts exist: `admin` / `admin123` and
`manager` / `manager123`. **Change those passwords** before going live:

```sh
cd backend
uv run python -m app.create_admin admin "Store Admin"   # asks for the new password
```

The same command adds a new account when the username doesn't exist yet.

## Data

Everything is stored in PostgreSQL. The tables and first-run data are created when
the backend starts. By default it connects to the database from `compose.yaml`;
to use another one, set `DATABASE_URL`:

```sh
DATABASE_URL=postgresql://user:password@host:5432/shop pnpm api
```

To start over with the original stock: `docker compose down -v` (deletes the data),
then `docker compose up -d`.

Moving from the old SQLite version? Copy `backend/data/shop.db` into PostgreSQL once:

```sh
cd backend
uv run python -m app.import_sqlite
```
