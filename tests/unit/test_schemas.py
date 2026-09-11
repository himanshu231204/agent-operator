import pytest
from pydantic import ValidationError as PydanticValidationError

from app.schemas.content import (
    ContentDraftToolInput,
    ContentDraftToolOutput,
    DraftUpdateRequest,
)
from app.schemas.research import Claim, Source
from app.schemas.task import TaskCreateRequest


def test_task_create_request_rejects_empty_instruction():
    with pytest.raises(PydanticValidationError):
        TaskCreateRequest(instruction="")


def test_claim_confidence_must_be_between_zero_and_one():
    source = Source(url="https://example.com", source_type="primary")
    with pytest.raises(PydanticValidationError):
        Claim(claim="x", source=source, evidence="y", confidence=1.5)


def test_claim_accepts_valid_confidence():
    source = Source(url="https://example.com", source_type="primary")
    claim = Claim(claim="x", source=source, evidence="y", confidence=0.9)
    assert claim.confidence == 0.9


def test_tone_preference_defaults_to_professional():
    inp = ContentDraftToolInput(platform="x", content="hello")
    assert inp.tone == "professional"


def test_tone_preference_accepts_all_valid_values():
    for tone in ("professional", "technical", "educational", "casual"):
        inp = ContentDraftToolInput(platform="x", content="hello", tone=tone)
        assert inp.tone == tone


def test_tone_preference_rejects_unknown():
    with pytest.raises(PydanticValidationError):
        ContentDraftToolInput(platform="x", content="hello", tone="rude")


def test_content_draft_tool_output_defaults():
    out = ContentDraftToolOutput(valid=True, formatted_content="hi")
    assert out.thread_posts == []
    assert out.issues == []


def test_draft_update_request_all_none_is_ok():
    req = DraftUpdateRequest()
    assert req.content is None
    assert req.status is None


def test_draft_update_request_rejects_bad_status():
    with pytest.raises(PydanticValidationError):
        DraftUpdateRequest(status="deleted")
