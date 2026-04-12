from app.services import ask_data


def test_compose_demo_narrative() -> None:
    text = ask_data.compose_demo_narrative("Revenue?", ["a", "b"], [[1, 2]])
    assert "Demo answer" in text
    assert "1 row" in text


def test_compose_live_count() -> None:
    text = ask_data.compose_live_narrative(
        "How many orders?",
        "orders",
        "count",
        ["row_count"],
        [[42]],
        None,
    )
    assert "42" in text
    assert "COUNT" in text or "count" in text.lower()


def test_confidence_tiers() -> None:
    assert ask_data.confidence_for("scan", None, False) == 0.88
    assert ask_data.confidence_for("count", 1, False) == 0.78
    assert ask_data.confidence_for("sum", 1, False) == 0.76
    assert ask_data.confidence_for("scan", 1, True) == 0.68


def test_narrative_and_meta_demo() -> None:
    answer, conf, warns = ask_data.narrative_and_meta(
        question="Test?",
        connection_id=None,
        columns=["x"],
        rows=[[1]],
        evidence={"query_kind": "demo", "table": "t", "selected_columns": None},
    )
    assert "Demo" in answer
    assert conf == 0.88
    assert any("Demo mode" in w for w in warns)
