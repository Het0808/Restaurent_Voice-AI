# PostgreSQL Database Design

## Principles

PostgreSQL is the only source of truth for availability and reservation state. All writes pass through typed business services and transactions; the LLM can invoke bounded tools but can never send or execute SQL. Store timestamps as timezone-aware UTC values and retain each restaurant's IANA timezone for interpretation and presentation.

## Schema

### `restaurants`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | VARCHAR(160) | Required |
| `timezone` | VARCHAR(64) | Required IANA name |
| `default_language` | VARCHAR(8) | `en`, `hi` or `gu` |
| `phone_number` | VARCHAR(32) | Nullable, unique when present |
| `is_active` | BOOLEAN | Default true |
| `created_at`, `updated_at` | TIMESTAMPTZ | Audit timestamps |

### `dining_tables`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `restaurant_id` | UUID | FK `restaurants`, required |
| `name` | VARCHAR(80) | Unique per restaurant |
| `min_capacity` | SMALLINT | Greater than zero |
| `max_capacity` | SMALLINT | At least `min_capacity` |
| `is_active` | BOOLEAN | Default true |
| `created_at`, `updated_at` | TIMESTAMPTZ | Audit timestamps |

### `customers`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `restaurant_id` | UUID | FK `restaurants`, required |
| `name` | VARCHAR(160) | Required |
| `phone_e164` | VARCHAR(20) | Required |
| `preferred_language` | VARCHAR(8) | Nullable, allowed languages only |
| `created_at`, `updated_at` | TIMESTAMPTZ | Audit timestamps |

Unique index on `(restaurant_id, phone_e164)`.

### `reservations`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | Primary key and public lookup token basis |
| `restaurant_id` | UUID | FK `restaurants`, required |
| `customer_id` | UUID | FK `customers`, required |
| `table_id` | UUID | FK `dining_tables`, nullable until assigned |
| `starts_at` | TIMESTAMPTZ | Required |
| `ends_at` | TIMESTAMPTZ | Required and after start |
| `party_size` | SMALLINT | Greater than zero |
| `status` | VARCHAR(24) | `pending`, `confirmed`, `cancelled`, `seated`, `completed`, `no_show` |
| `special_requests` | TEXT | Nullable, length limited by application |
| `source` | VARCHAR(24) | `voice`, `web`, `staff` |
| `language` | VARCHAR(8) | Language used while booking |
| `version` | INTEGER | Optimistic concurrency counter |
| `created_at`, `updated_at`, `cancelled_at` | TIMESTAMPTZ | Audit timestamps |

Indexes: `(restaurant_id, starts_at, status)`, `(customer_id, starts_at DESC)`, and `(table_id, starts_at, ends_at)` for active reservations. Prevent overlapping active reservations for a table with a PostgreSQL exclusion constraint over `tstzrange(starts_at, ends_at, '[)')`; assignment and mutation also run transactionally.

### `reservation_events`

| Column | Type | Constraints / purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `reservation_id` | UUID | FK `reservations`, required |
| `event_type` | VARCHAR(32) | Created, modified, cancelled, status changed |
| `actor_type` | VARCHAR(24) | Assistant, customer, staff, system |
| `correlation_id` | UUID | Trace link |
| `changes` | JSONB | Allowlisted before/after business fields; no secrets |
| `created_at` | TIMESTAMPTZ | Immutable timestamp |

### `idempotency_keys`

| Column | Type | Constraints / purpose |
|---|---|---|
| `restaurant_id` | UUID | Composite primary key |
| `key` | VARCHAR(128) | Composite primary key |
| `operation` | VARCHAR(32) | Operation name |
| `request_hash` | VARCHAR(64) | Reject key reuse with different arguments |
| `resource_id` | UUID | Nullable until completion |
| `response_code` | VARCHAR(32) | Stable result |
| `expires_at`, `created_at` | TIMESTAMPTZ | Cleanup and audit |

## Availability and mutation rules

- Availability queries consider only active tables with sufficient capacity and reservations in blocking statuses.
- The MVP assigns one table per reservation and uses a configurable default duration.
- Creation runs customer upsert, availability selection, reservation insert and event insert in one transaction.
- Modification locks the reservation, checks `version`, verifies new availability excluding itself, updates it and records an event in one transaction.
- Cancellation is idempotent: an already-cancelled reservation returns its current authoritative state.
- A database commit must complete before a tool returns `confirmed` or `cancelled` success.
- Expected conflicts return structured alternatives; they do not leak SQL or database details.

## Data boundaries

FAQ documents, chunks and embeddings belong in the retrieval subsystem, not reservation tables. Raw audio is not stored in PostgreSQL by default. Conversation transcripts and caller PII are retained only when a documented operational need, consent basis and deletion policy exist.

## Migration and recovery plan

Alembic will own forward migrations. Production changes use backups, reviewed migrations and rollback/roll-forward procedures. Database users are separated into migration and runtime roles; the runtime role receives only required CRUD privileges. Automated backups and point-in-time recovery are required before production launch.
