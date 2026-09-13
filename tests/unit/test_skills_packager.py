"""Unit tests for skills packager."""

from __future__ import annotations

import os
import tempfile

import pytest
from skills.packager import _parse_skill_md, validate_skills


class TestParseSkillMd:
    def test_parse_minimal_skill(self):
        content = """\
# Skill: Test Skill

## Purpose
A test skill for validation.

## Inputs
```json
{
  "input1": "string — first input"
}
```

## Outputs
```json
{
  "output1": "string — first output"
}
```

## Required Tools
- tool_a
- tool_b

## Required Permissions
- HIGH risk — REQUIRES explicit user approval before execution
"""
        contract = _parse_skill_md(content, "test-skill")
        assert contract.name == "test-skill"
        assert "test skill" in contract.purpose.lower()
        assert "input1" in contract.inputs
        assert "output1" in contract.outputs
        assert "tool_a" in contract.tools
        assert "tool_b" in contract.tools
        assert contract.risk_level == "high"

    def test_parse_no_tools(self):
        content = """\
# Skill: Simple Skill

## Purpose
Does something simple.

## Inputs
```json
{}
```

## Outputs
```json
{}
```

## Required Permissions
- LOW risk
"""
        contract = _parse_skill_md(content, "simple-skill")
        assert contract.tools == []
        assert contract.risk_level == "low"


class TestValidateSkills:
    def test_validate_all_skills(self):
        """Validate all skills in the repository."""
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
        manifest = validate_skills(skills_dir)

        assert manifest.version == "1.0"
        assert len(manifest.skills) >= 6  # At least 6 skills

        skill_names = {s.name for s in manifest.skills}
        assert "web-research" in skill_names
        assert "content_generation" in skill_names
        assert "x_publishing" in skill_names
        assert "linkedin_publishing" in skill_names

    def test_validate_empty_dir(self):
        """Validate with empty skills directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = validate_skills(tmpdir)
            assert manifest.skills == []

    def test_validate_nonexistent_dir(self):
        """Validate with nonexistent directory raises error."""
        with pytest.raises(FileNotFoundError):
            validate_skills("/nonexistent/path")

    def test_skill_has_required_fields(self):
        """Each skill should have a name, purpose, and risk level."""
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
        manifest = validate_skills(skills_dir)

        for skill in manifest.skills:
            assert skill.name, "Skill must have a name"
            assert skill.purpose, "Skill must have a purpose"
            assert skill.risk_level in ("low", "medium", "high"), \
                f"Skill {skill.name} has invalid risk level: {skill.risk_level}"
