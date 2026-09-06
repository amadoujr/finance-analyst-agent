"""HITL sensitivity detection."""

from finance_analyst.graph.sensitivity import is_sensitive_question


def test_buy_question_is_sensitive() -> None:
    assert is_sensitive_question("Should I buy AAPL stock?")


def test_french_buy_is_sensitive() -> None:
    assert is_sensitive_question("Dois-je acheter des actions Apple ?")


def test_risk_factors_not_sensitive() -> None:
    assert not is_sensitive_question("What are the main risk factors for Apple?")


def test_roe_not_sensitive() -> None:
    assert not is_sensitive_question("What is Apple's ROE?")
