from app.services import ask_data


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
