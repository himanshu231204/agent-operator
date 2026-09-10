from app.content.validators import content_hash, validate_content


def test_valid_content_passes():
    result = validate_content("x", "A short, valid post.")
    assert result.valid
    assert result.issues == []


def test_empty_content_is_invalid():
    result = validate_content("x", "   ")
    assert not result.valid
    assert result.issues[0].check == "formatting"


def test_content_over_platform_limit_is_invalid():
    result = validate_content("x", "a" * 281)
    assert not result.valid
    assert any(issue.check == "length" for issue in result.issues)


def test_malformed_link_is_flagged():
    result = validate_content("linkedin", "Check this out: https://not a url")
    assert not result.valid
    assert any(issue.check == "links" for issue in result.issues)


def test_duplicate_content_is_flagged():
    content = "Same content twice"
    existing = {content_hash(content)}
    result = validate_content("x", content, existing_hashes=existing)
    assert not result.valid
    assert any(issue.check == "duplicates" for issue in result.issues)
