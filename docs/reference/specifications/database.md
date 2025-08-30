# DB Utilities Specification

Purpose: Define the database utility interfaces and behaviors used by the CLI/API orchestration.
These utilities target Supabase (Postgres) and are designed for reliability, clarity, and testability.

## Environment & Credentials

- Required env vars (read from `.env` or process env):
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
- Behavior:
  - Validate presence at process start when first DB interaction occurs.
  - Provide clear error messages if missing.

## Modules and Responsibilities

- `src/jambandnerd/db/connection.py`
  - `get_supabase_client() -> SupabaseClient`
    - Validates env, constructs, and returns a singleton client.
  - `validate_environment() -> None`
    - Raises descriptive error if required env missing.

- `src/jambandnerd/db/operations.py`
  - `get_table_schema(table_name: str) -> TableSchema`
    - Returns column metadata: name, data_type, nullable, default, primary_key.
  - `fetch_existing_ids(table_name: str, id_column: str, since: Optional[str] = None) -> set[str | int]`
    - Optional date filter for incremental checks.
  - `bulk_insert_dataframe(table_name: str, df: pandas.DataFrame, chunk_size: int = 5000) -> InsertResult`
    - Inserts all rows; caller ensures schema compatibility.
  - `upsert_dataframe(table_name: str, df: pandas.DataFrame, conflict_columns: list[str],
     chunk_size: int = 5000) -> UpsertResult`
    - Upserts rows using provided conflict target(s).
  - `begin_run(model_slug: Optional[str]) -> RunContext`
    - Returns a `run_id` (uuid) and `generated_at` timestamp for consistent auditing.

- `src/jambandnerd/db/validation.py`
  - `ValidationReport` (dataclass)
    - `missing_columns: list[str]`
    - `extra_columns: list[str]`
    - `type_mismatches: list[TypeMismatch]`
    - `nullable_violations: list[str]`
    - `row_count: int`
    - `is_valid: bool`
  - `TypeMismatch` (dataclass)
    - `column: str`
    - `expected_type: str`
    - `observed_type: str`
    - `example_values: list[str]`
  - `validate_dataframe_against_table(df: pandas.DataFrame, table_name: str) -> ValidationReport`
    - Compares df columns/types/nullability to target table.
  - `coerce_df_types(df: pandas.DataFrame, schema: TableSchema) -> pandas.DataFrame`
    - Applies safe coercions where possible (e.g., strings like "true"/"false"/"" to booleans;
      numeric-like strings to integers), returning a new DataFrame.

## Data Type Conventions (pandas ↔ Postgres)

- Strings: Postgres `text` ←→ pandas `object[string]`
- Integers: Postgres `integer/bigint` ←→ pandas nullable `Int64`
- Booleans: Postgres `boolean` ←→ pandas nullable `boolean`
- Timestamps: Postgres `timestamptz` ←→ pandas `datetime64[ns, UTC]`

Coercion rules:

- Empty strings in integer/boolean columns → NULL
- Boolean-like strings {"true","false","1","0","yes","no"} → boolean
- Non-coercible values are left as-is; they appear in `type_mismatches`.

## Table Naming (summary)

- Raw: `{band}_songs_raw`, `{band}_shows_raw`, `{band}_setlists_raw`
- Predictions: `predictions_{model_slug}`
- Accuracy: `accuracy_{model_slug}`

## Error Handling & Retries

- Network/HTTP errors: retry with exponential backoff (up to 3 attempts) where safe.
- Validation failures: raise with actionable message including `ValidationReport` summary.
- All operations log: start/end, row counts, and timing.

## Logging & Observability

- Log shape: `[timestamp] LEVEL module.function: message`
- Include `run_id` and `model_slug` (when applicable) in logs for correlation.

## Testing Guidelines (docs only)

- Unit tests mock Supabase client and verify:
  - Correct chunking and upsert behavior.
  - Validation reports for representative schemas.
  - Coercion logic on mixed-type columns.