# UNDERGROUND

React + Vite (with React Compiler) storefront, with a Python FastAPI backend in `backend/`.

## Run it

Needs Docker (for PostgreSQL), [uv](https://docs.astral.sh/uv/) and pnpm.

First time only:

```sh
docker compose up -d                 # PostgreSQL on localhost:5432 (user/password/db: shop)
cd backend
cp .env.example .env                 # then set JWT_SECRET_KEY (the file says how)
uv run alembic upgrade head          # create the tables
uv run python -m app.cli seed        # add the sample products
uv run python -m app.cli create-admin --email you@shop.dz --name "Your Name"
```

Then, in two terminals from the project folder (or from `frontend/`):

```sh
pnpm api                                   # 1. Backend — http://localhost:8000
pnpm install:frontend && pnpm dev          # 2. Frontend — http://localhost:5173
```

Vite forwards every `/api/...` request to the backend, so both must be running.
To point it at another backend: `API_URL=http://localhost:9000 pnpm dev`.
API docs (try requests in the browser): http://localhost:8000/docs

## Tests

```sh
cd backend
uv run pytest            # needs PostgreSQL running; uses (and wipes) the shop_test database
cd ../frontend
pnpm lint && pnpm build
```

## How a sale works

Placing an order sets its items aside straight away, so two customers can never
buy the same last item. Open an order in **Admin → Orders** to move it along:

```
pending ─► confirmed ─► processing ─► shipped ─► delivered
   │           │             │            │           │
   └───────────┴─────────────┴─► cancelled └─► returned ◄┘
```

- **Cancelled** and **returned** orders put their items back in stock.
- **Revenue** on the dashboard counts delivered orders only (cash on delivery).

## Products

Add, edit and delete products in **Admin → Products**, including uploading a photo
(saved in `backend/data/uploads/`). The shop loads products from the backend, so
changes show up straight away. Deleting hides a product but keeps it in old orders.

## Admin accounts

Sign in at **/admin** with your email. There is no sign-up and no default account;
accounts are created on the server:

```sh
cd backend
uv run python -m app.cli create-admin --email you@shop.dz --name "Your Name"              # admin
uv run python -m app.cli create-admin --email helper@shop.dz --name "Helper" --role staff # orders only
```

It asks for the password. Running it again for an existing email resets that
account's name, role and password (and signs it out everywhere).

## Data

Everything is stored in PostgreSQL. The connection comes from `DATABASE_URL` in
`backend/.env`. After pulling changes that touch `backend/alembic/versions/`, run
`uv run alembic upgrade head` again.

To start over: `docker compose down -v` (deletes the data), `docker compose up -d`,
then repeat the first-time steps above.
