# Crypto Deposit Watcher (Sepolia Testnet Only)

Django REST Framework and PostgreSQL learning project that scans Ethereum Sepolia for native ETH deposits, waits for confirmations, records an internal ledger credit exactly once, and provides a controlled withdrawal approval queue.

> **TESTNET ONLY.** Not audited or suitable for real funds. Never use production RPC endpoints, seed phrases, or private keys. Withdrawals are approved and reserved internally but are not signed or broadcast.

## Features
- Sepolia-only RPC guard (chain ID 11155111)
- Native ETH transaction scanning with Web3.py
- Persistent block checkpoints, confirmation tracking, receipt and canonical block-hash validation
- Reorg detection; manual reconciliation alert if a credited deposit is affected
- Atomic idempotent ledger credits protected by database uniqueness constraints
- Per-user public deposit-address registry and deposit/balance APIs
- Withdrawal idempotency, balance reservation, configured test ETH ceilings and reviewer approvals
- Docker Compose, PostgreSQL, Django admin and pytest tests

## Stack
Python 3.12, Django, Django REST Framework, PostgreSQL, Web3.py, Docker Compose, pytest.

## Run
1. Copy `.env.example` to `.env`.
2. Set `ETH_RPC_URL` to a Sepolia RPC endpoint; keep `EXPECTED_CHAIN_ID=11155111`.
3. Replace the local Django secret.
4. Start the services:

```powershell
docker compose up --build -d
docker compose exec api python manage.py createsuperuser
docker compose logs -f watcher
```

Admin: http://localhost:8001/admin/

Tests:

```powershell
docker compose exec api pytest
```

## API (authentication required by default)
- `GET /api/health/`
- `GET /api/deposit-addresses/`
- `GET /api/deposits/`
- `GET /api/balance/`
- `POST /api/dev/deposit-addresses/` (staff-only public-address registration helper)
- `POST /api/withdrawals/`
- `GET /api/withdrawals/`
- `POST /api/withdrawals/{id}/approve/` (staff approval)

## Limitations and security
- Native ETH top-level transactions only; ERC-20 logs, internal transfers and token deposits are not implemented.
- HD address derivation and transaction signing are not wired. Only public addresses are registered. Never store a seed phrase in the application database.
- Withdrawal requests are reserved and approved but not broadcast. Broadcasting needs isolated key custody, nonce/gas handling, signing and operational safeguards.
- Reorgs before credit are marked REORGED. A reorg affecting an already credited deposit requires controlled manual ledger reconciliation; history is not silently erased.
- Confirmation counts reduce risk but do not guarantee absolute finality.
- The local ledger is authoritative. For a separate PlayLedger service, integrate through a transactional outbox and idempotent receiver, not an untracked dual write.
- This code has not been audited or verified against a live Sepolia RPC. Run automated tests and local end-to-end checks before relying on it.

Never commit `.env`, RPC credentials, mnemonic phrases, private keys or real wallet material. Use faucet-funded Sepolia accounts only.
