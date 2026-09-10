import pytest
from pydantic import ValidationError

from app.schemas.research import Claim, Source
from app.schemas.task import TaskCreateRequest


def test_task_create_request_rejects_empty_instruction():
    with pytest.raises(ValidationError):
        TaskCreateRequest(instruction="")


def test_claim_confidence_must_be_between_zero_and_one():
    source = Source(url="https://example.com", source_type="primary")
    with pytest.raises(ValidationError):
        Claim(claim="x", source=source, evidence="y", confidence=1.5)


def test_claim_accepts_valid_confidence():
    source = Source(url="https://example.com", source_type="primary")
    claim = Claim(claim="x", source=source, evidence="y", confidence=0.9)
    assert claim.confidence == 0.9
