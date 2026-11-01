# PlayLedger — Virtual-Credit Wallet & Double-Entry Ledger

PlayLedger is an educational backend project demonstrating how to build a transaction-safe virtual-credit wallet. It uses Django REST Framework, PostgreSQL, React, Docker Compose, and automated tests. It does **not** process real money and credits have no cash or redemption value.

## Features

- User registration and token authentication
- Automatically created user wallet (including staff/superuser accounts)
- Integer-only virtual-credit balances
- Double-entry ledger: every posted transaction's entries sum to zero
- Atomic transfers protected by PostgreSQL row locks
- Idempotency keys and request fingerprints to prevent duplicate processing
- Admin-only credit issuance from a system issuance account
- Admin-only account freeze/unfreeze/close controls
- Admin-only transaction reversal with a compensating ledger transaction
- Read-only transaction history and details, scoped to the signed-in user's wallet
- Admin-only reconciliation of transaction totals and cached balances
- Audit records for transfers, credit issuance, reversals, and reconciliation runs
- Django admin with posted ledger entries and transactions read-only
- React dashboard, Docker Compose, health check, and GitHub Actions CI
- API throttling and database constraints

## Quick start (Docker — recommended)

Prerequisites: Docker Desktop with Compose enabled.

1. Copy `.env.example` to `.env`.
2. For local development, the example values work as-is. Do not use them for a public deployment.
3. From this folder run:

   ```bash
   docker compose up --build -d
   docker compose ps
   docker compose logs -f api
   ```

4. Open the React app at http://localhost:5173 and the API health endpoint at http://localhost:8000/api/health/.
5. Create a Django admin account:

   ```bash
   docker compose exec api python manage.py createsuperuser
   ```

6. Log in to the admin site at http://localhost:8000/admin/.
7. Register demo users from the frontend. Issue virtual credits through the staff-only endpoint described below, using an admin token.

Stop services with `docker compose down`. Database data persists in the `postgres_data` volume. To delete the local development database too, use `docker compose down -v` (destructive).

## Local backend setup (Windows PowerShell)

Install Python 3.12+, PostgreSQL, and Git. Create a PostgreSQL database and user, then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DB_NAME = "playledger"
$env:DB_USER = "playledger"
$env:DB_PASSWORD = "your-local-password"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DJANGO_SECRET_KEY = "a-long-local-development-secret"
python manage.py migrate
python manage.py bootstrap_system_accounts
python manage.py createsuperuser
python manage.py runserver
```

If PowerShell blocks activation, use `cmd.exe` and run `.venv\Scripts\activate.bat`, or invoke `.venv\Scripts\python.exe` directly. The project falls back to SQLite if `DB_HOST` is unset for a quick smoke test; **use PostgreSQL for meaningful concurrency tests**, because SQLite does not provide equivalent row-locking semantics.

Frontend local setup in a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000/api`; set `VITE_API_URL` if your API is elsewhere.

## API guide

All protected routes use DRF token authentication:

`Authorization: Token <token>`

### Register

`POST /api/auth/register/`

```json
{"username":"alice","password":"a-strong-password","email":"alice@example.com"}
```

Returns `user_id`, `username`, and an authentication `token`. New wallets start at zero credits.

### Login

`POST /api/auth/login/`

```json
{"username":"alice","password":"a-strong-password"}
```

Returns a token.

### Current user

`GET /api/auth/me/` returns the authenticated user ID, username, and staff flag.

### Wallet

`GET /api/wallet/` — authenticated user's wallet.

### Transfer credits

`POST /api/transfers/`

Headers: `Authorization: Token <token>` and `Idempotency-Key: a-unique-key`

```json
{"recipient_id":2,"amount":25,"description":"Demo transfer"}
```

The sender is always derived from the authenticated user, not from client-provided sender IDs. Amounts must be positive integers. Reusing a key with the same request returns the existing transaction; reusing it with a different request is rejected. Keep a key stable when retrying the *same* logical request.

### Transaction history

- `GET /api/transactions/` — up to the latest 100 transactions touching your wallet; optional `?kind=transfer` filter.
- `GET /api/transactions/<uuid>/` — transaction detail only if it touches your wallet.
- `GET /api/accounts/` — your accounts.

### Admin-only virtual-credit issuance

`POST /api/admin/credits/issue/`

Headers: staff token and `Idempotency-Key: issue-alice-001`

```json
{"recipient_id":2,"amount":1000,"description":"Demo credits"}
```

The endpoint is restricted to Django staff users. Never expose credit issuance to ordinary users. The issuance system account is initialized automatically in Docker or manually via `python manage.py bootstrap_system_accounts`.

### Admin-only reconciliation

`GET /api/admin/reconciliation/` reports unbalanced transactions and cached-vs-ledger balance mismatches. It is read-only and returns HTTP 409 when discrepancies are found; investigate the report rather than silently editing posted entries.

### Admin-only account status

`POST /api/admin/accounts/<account_id>/status/` with `{"status":"frozen"}` (or `active` / `closed`) freezes or reactivates a wallet. The endpoint locks the account row and writes an audit event. Closed accounts cannot transfer.

### Admin-only reversal

`POST /api/admin/transactions/<uuid>/reverse/` with an `Idempotency-Key` creates compensating entries. It refuses duplicate reversals and refuses a reversal that would make a user wallet negative. A reversal does not delete or edit the original entries.

### Health

`GET /api/health/` checks database connectivity.

## Accounting invariants

1. Every posted transaction has at least two entries.
2. The signed sum of entries in each transaction is zero.
3. User wallet balances cannot be negative.
4. Ledger entries are append-only in the application and Django admin; corrections use reversals.
5. Balance updates and entries are written in the same database transaction.
6. Transfer account rows are locked in ascending ID order to reduce deadlock risk.
7. Idempotency keys are scoped to the authenticated actor, and request fingerprints prevent conflicting key reuse.

The model's `save()`/`delete()` overrides and admin settings provide application-level immutability, not tamper-proof database immutability against a database owner. A production-grade system should add stricter database permissions/triggers and operational controls.

## Tests

```bash
pytest
```

The included tests cover issuance/transfer accounting, idempotent retry, insufficient funds, wallet registration, and wallet retrieval. Extend the suite with PostgreSQL-backed `TransactionTestCase`/`pytest` tests using independent connections to validate concurrent overspending and deadlock retry behavior. Do not use SQLite to claim concurrency safety.

## Project structure

```text
config/                 Django settings, URLs, WSGI
accounts/               registration and health check
wallets/                account model and wallet APIs
ledger/                 transactions, entries, services, admin, reconciliation
ledger/management/      system-account bootstrap command
ledger/tests/            core accounting tests
frontend/                React/Vite dashboard
.github/workflows/ci.yml PostgreSQL-backed CI
Dockerfile               Django API container
compose.yaml              PostgreSQL + API + React development stack
```

## Security and production notes

This is a learning project, not a production financial ledger. Before any production use, add proper secret management, HTTPS, secure token lifecycle/revocation, request-size limits, robust error monitoring, backups/restore drills, database role separation, immutable database-level posting controls, pagination, and stronger concurrent integration tests. Rotate the development secret and database password before exposing any service publicly.
