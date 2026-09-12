# Skill: Content Generation

## Purpose
Draft platform-aware content (X/Twitter posts, LinkedIn posts, threads)
from validated research evidence. Never publishes — creates drafts only.

## Inputs
```json
{
  "research": { "summary": "...", "claims": [...] },
  "platform": "x | linkedin",
  "tone": "professional | technical | educational | casual",
  "max_length": "int (optional) — override platform default"
}
```

## Outputs
```json
{
  "draft_id": "uuid",
  "content": "string — the draft text",
  "platform": "x | linkedin",
  "character_count": 280,
  "warnings": ["any quality check warnings"]
}
```

## Required Tools
- ContentDraftTool
- Platform content validators

## Required Permissions
- MEDIUM risk (creates a draft, no external side effects)
- No user approval required to draft; approval required to publish

## Safety Constraints
- Never invent statistics, quotes, sources, or events not in the research input
- Validate platform-specific length constraints
- Detect and reject accidental duplicate content
- Drafting and publishing are separate permissions — never call a publish tool

## Examples
- "Draft an X post about the PostgreSQL research findings"
- "Create a LinkedIn post summarising the AI agent framework comparison"

## Failure Modes
- Research input empty → return ValidationError
- Content exceeds platform limit after generation → truncate and warn
- Safety policy violation → raise ValidationError (non-retryable)
