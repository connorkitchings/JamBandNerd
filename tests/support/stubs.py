"""Shared test stubs for Supabase client and query builder chains.

Import these in test files instead of re-implementing ad-hoc MagicMock
wrappers.  Each stub models the Supabase query-builder chain:

    client.table(...).select(...).eq(...).order(...).limit(...).execute()

with configurable response data, filter semantics, and ordering behaviour.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class SupabaseResponseStub:
    """Configurable stub response returned by `.execute()`."""

    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data: list[dict[str, Any]] = data or []


class SupabaseQueryStub:
    """Lightweight query builder chain stub.

    Each method in the chain returns ``self`` so callers can chain
    ``.table(...).select(...).eq(...).execute()`` naturally.  The
    ``response`` attribute controls what ``.execute()`` returns.
    """

    def __init__(
        self,
        *,
        response: SupabaseResponseStub | None = None,
        table_name: str = "",
    ) -> None:
        self._response = response or SupabaseResponseStub()
        self._table_name = table_name
        self._select_columns = "*"
        self._filters: list[tuple[Any, ...]] = []
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._limit_val: int | None = None
        self._range_vals: tuple[int, int] | None = None
        self._in_values: list[Any] | None = None
        self._is_delete: bool = False

    # -- chain methods ---------------------------------------------------

    def select(self, columns: str = "*") -> "SupabaseQueryStub":
        self._select_columns = columns
        return self

    def eq(self, column: str, value: Any) -> "SupabaseQueryStub":
        self._filters.append(("eq", column, value))
        return self

    def gte(self, column: str, value: Any) -> "SupabaseQueryStub":
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column: str, value: Any) -> "SupabaseQueryStub":
        self._filters.append(("lte", column, value))
        return self

    def lt(self, column: str, value: Any) -> "SupabaseQueryStub":
        self._filters.append(("lt", column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> "SupabaseQueryStub":
        self._in_values = values
        self._filters.append(("in", column, values))
        return self

    def neq(self, column: str, value: Any) -> "SupabaseQueryStub":
        self._filters.append(("neq", column, value))
        return self

    def order(self, column: str, *, desc: bool = False) -> "SupabaseQueryStub":
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "SupabaseQueryStub":
        self._limit_val = n
        return self

    def range(self, start: int, end: int) -> "SupabaseQueryStub":
        self._range_vals = (start, end)
        return self

    def delete(self) -> "SupabaseQueryStub":
        self._is_delete = True
        return self

    def insert(
        self, records: list[dict[str, Any]] | dict[str, Any]
    ) -> "SupabaseQueryStub":
        return self

    def upsert(self, records: list[dict[str, Any]], **_: Any) -> "SupabaseQueryStub":
        return self

    def execute(self) -> SupabaseResponseStub:
        return self._response


class SupabaseClientStub:
    """Stub Supabase client that returns ``SupabaseQueryStub`` chains.

    Args:
        response: Default response for all table queries.
        table_stubs: Optional mapping of table name -> per-table query stub
            (useful when a test calls multiple tables with different data).
    """

    def __init__(
        self,
        *,
        response: SupabaseResponseStub | None = None,
        table_stubs: dict[str, SupabaseQueryStub] | None = None,
    ) -> None:
        self._default_response = response or SupabaseResponseStub()
        self._table_stubs = table_stubs or {}

    def table(self, name: str) -> SupabaseQueryStub:
        return self._table_stubs.get(
            name,
            SupabaseQueryStub(
                response=self._default_response,
                table_name=name,
            ),
        )

    def rpc(
        self, _name: str, _params: dict[str, Any] | None = None
    ) -> "SupabaseRpcStub":
        return SupabaseRpcStub()


class SupabaseRpcStub:
    """Stub for Supabase RPC calls."""

    def __init__(self, result: Any | None = None) -> None:
        self._result = result

    def execute(self) -> MagicMock:
        mock = MagicMock()
        mock.data = self._result
        return mock


def make_client_stub(
    *,
    table_data: dict[str, list[dict[str, Any]]] | None = None,
) -> SupabaseClientStub:
    """Create a ``SupabaseClientStub`` with per-table response data."""
    table_stubs: dict[str, SupabaseQueryStub] = {}
    if table_data:
        for name, data in table_data.items():
            table_stubs[name] = SupabaseQueryStub(
                response=SupabaseResponseStub(data=data),
                table_name=name,
            )
    return SupabaseClientStub(table_stubs=table_stubs)
