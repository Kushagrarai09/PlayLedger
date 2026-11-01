# PlayLedger architecture notes

## Transaction boundary

`ledger.services` is the only application layer that posts money-like entries. The API layer authenticates the caller, validates request shape, checks staff permissions where required, and maps expected business failures to HTTP responses. The service layer runs account mutations, transaction creation, and ledger-entry creation in a single `transaction.atomic()` block.

## Transfer invariants

- Sender is derived from `request.user`.
- Amount is a positive integer.
- Both accounts are locked in ascending primary-key order.
- The sender balance is checked only after locks are acquired.
- Cached balances and ledger entries are committed together.
- Entries sum to zero for each posted transaction.
- A successful idempotent retry returns the original transaction.
- Reusing a key with a different request fingerprint is rejected.

## Why a cached balance exists

Summing the entire ledger for every wallet request is easy to reason about but becomes expensive as the history grows. `Account.balance_minor` is a cache updated in the same transaction as ledger entries. Reconciliation independently recalculates balances from the entries and reports mismatches.

## Operational limits

This is a learning project. The service provides application-level append-only behavior, not cryptographic tamper evidence or protection from a database superuser. The included reconciliation endpoint is synchronous and suitable only for a small demo dataset. For larger datasets, run reconciliation in a background worker and persist a run record. For production, restrict database roles, add database triggers or stored procedures for posting invariants, build backup/restore drills, monitor errors, paginate all endpoints, and test against PostgreSQL under load.
