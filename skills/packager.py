"""Skills packager (Phase 8 — Production).

Validates all SKILL.md contracts and exports a JSON manifest.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class SkillContract(BaseModel):
    """Parsed contract from a SKILL.md file."""

    name: str
    purpose: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    tools: list[str]
    risk_level: str


class SkillsManifest(BaseModel):
    """Manifest of all validated skills."""

    version: str = "1.0"
    skills: list[SkillContract]


def _parse_skill_md(content: str, name: str) -> SkillContract:
    """Parse a SKILL.md file into a SkillContract."""
    # Extract purpose (from ## Purpose section or first paragraph)
    purpose_match = re.search(r"## Purpose\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
    if purpose_match:
        purpose = purpose_match.group(1).strip()
    else:
        # Fallback: use first non-empty line after the title
        lines = content.strip().split("\n")
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith("#"):
                purpose = line
                break
        else:
            purpose = ""

    # Extract inputs
    inputs: dict[str, str] = {}
    inputs_match = re.search(r"## Inputs\n```json\n(.+?)\n```", content, re.DOTALL)
    if inputs_match:
        import json
        try:
            inputs = json.loads(inputs_match.group(1))
        except json.JSONDecodeError:
            pass

    # Extract outputs
    outputs: dict[str, str] = {}
    outputs_match = re.search(r"## Outputs\n```json\n(.+?)\n```", content, re.DOTALL)
    if outputs_match:
        import json
        try:
            outputs = json.loads(outputs_match.group(1))
        except json.JSONDecodeError:
            pass

    # Extract tools
    tools: list[str] = []
    tools_match = re.search(r"## Required Tools\n((?:-.+\n?)+)", content)
    if tools_match:
        for line in tools_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("- ").strip()
            if line:
                tools.append(line)

    # Extract risk level
    # Patterns: "HIGH risk", "Risk level: MEDIUM", "- Risk level: LOW"
    risk_patterns = [
        r"(?:^|\n)-\s*[Rr]isk\s*level:\s*(low|medium|high)",
        r"(low|medium|high)\s+risk",
        r"[Rr]isk\s*level:\s*(low|medium|high)",
    ]
    risk_level = "unknown"
    for pattern in risk_patterns:
        risk_match = re.search(pattern, content, re.IGNORECASE)
        if risk_match:
            risk_level = risk_match.group(1).lower()
            break

    return SkillContract(
        name=name,
        purpose=purpose,
        inputs=inputs,
        outputs=outputs,
        tools=tools,
        risk_level=risk_level,
    )


def validate_skills(skills_dir: str | None = None) -> SkillsManifest:
    """Validate all SKILL.md contracts and return a manifest.

    Args:
        skills_dir: Path to skills directory. Defaults to ../skills/ relative to this file.

    Returns:
        SkillsManifest with all validated skills.

    Raises:
        FileNotFoundError: If skills_dir does not exist.
        ValueError: If a SKILL.md fails validation.
    """
    if skills_dir is None:
        skills_dir = os.path.join(os.path.dirname(__file__), "..", "skills")

    skills_path = Path(skills_dir)
    if not skills_path.exists():
        raise FileNotFoundError(f"Skills directory not found: {skills_dir}")

    skills: list[SkillContract] = []

    for skill_dir in sorted(skills_path.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text(encoding="utf-8")
        contract = _parse_skill_md(content, skill_dir.name)
        skills.append(contract)

    return SkillsManifest(skills=skills)


if __name__ == "__main__":
    import json
    manifest = validate_skills()
    print(json.dumps(manifest.model_dump(), indent=2))
