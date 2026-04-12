import pytest

from app.services.sql_policy import extract_sql_from_llm, prepare_readonly_select


def test_extract_sql_from_fence() -> None:
    raw = """Here is the query:
```sql
SELECT id FROM users
```
"""
    assert "SELECT id FROM users" in extract_sql_from_llm(raw)


def test_prepare_select_adds_limit_postgres() -> None:
    sql = prepare_readonly_select(
        "SELECT a FROM public.orders",
        source_type="postgresql",
        allowed_table_names={"public.orders"},
        max_rows=17,
    )
    assert "LIMIT" in sql.upper()
    assert "17" in sql


def test_prepare_rejects_insert() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        prepare_readonly_select(
            "INSERT INTO t VALUES (1)",
            source_type="postgresql",
            allowed_table_names={"t"},
            max_rows=10,
        )


def test_prepare_allows_cte() -> None:
    sql = prepare_readonly_select(
        "WITH x AS (SELECT 1 AS n) SELECT n FROM x",
        source_type="postgresql",
        allowed_table_names={"real_table"},
        max_rows=5,
    )
    assert "x" in sql.lower()
