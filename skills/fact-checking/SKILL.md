# Skill: Fact Checking

## Purpose
Validate the claims in a content draft against available source evidence.
Returns an annotated result flagging unsupported or contradicted claims.

## Inputs
```json
{
  "draft": "string — the content to fact-check",
  "research": { "claims": [...], "sources_consulted": [...] },
  "strictness": "low | medium | high (default medium)"
}
```

## Outputs
```json
{
  "passed": true,
  "annotated_draft": "string — draft with inline [SUPPORTED] / [UNSUPPORTED] markers",
  "issues": [
    {
      "claim": "string",
      "status": "supported | unsupported | contradicted | unverifiable",
      "evidence": "string (if supported)",
      "contradiction": "string (if contradicted)"
    }
  ]
}
```

## Required Tools
- TavilySearchResults (cross-check lookup)
- WebFetchTool

## Required Permissions
- LOW risk (read-only)
- No user approval required

## Safety Constraints
- Never fabricate supporting evidence
- Surface contradictions rather than silently resolving them
- A claim is only SUPPORTED if the evidence is explicit, not inferred

## Examples
- Verify claims in a PostgreSQL best-practices LinkedIn post
- Check statistics cited in a research summary

## Failure Modes
- Search unavailable → mark claims as UNVERIFIABLE, do not fail the draft
- Contradicted claim found → flag as contradicted, let user decide
