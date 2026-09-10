from app.policies.approval import build_approval_request, requires_approval
from app.policies.risk import RiskLevel


def test_low_and_medium_risk_do_not_require_approval():
    assert not requires_approval(RiskLevel.LOW)
    assert not requires_approval(RiskLevel.MEDIUM)


def test_high_risk_requires_approval():
    assert requires_approval(RiskLevel.HIGH)


def test_build_approval_request_carries_risk_and_content():
    request = build_approval_request(
        action="Publish X post",
        target="user's X account",
        risk_level=RiskLevel.HIGH,
        content={"text": "hello"},
        reason="user requested publish",
    )
    assert request.risk_level == "high"
    assert request.content == {"text": "hello"}
