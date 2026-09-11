# Skill: LinkedIn Publishing

## Purpose
Publish an approved draft to LinkedIn via the official API.
Always requires explicit user approval before any external publish action.

## Inputs
```json
{
  "draft_id": "uuid — the pre-approved draft",
  "idempotency_key": "string — caller-supplied deduplication key"
}
```

## Outputs
```json
{
  "post_id": "string",
  "url": "string",
  "published_at": "ISO 8601 timestamp",
  "verified": true,
  "verification_details": { "content_match": true, "url_accessible": true }
}
```

## Required Tools
- LinkedInPublishTool (HIGH risk, requires_approval=True)
- VerificationTool

## Required Permissions
- HIGH risk — REQUIRES explicit user approval before execution
- Requires LinkedIn OAuth2 authentication

## Safety Constraints
- Never publish without a confirmed approval in ExecutionContext.approved_actions
- Check idempotency_key before calling the API to prevent duplicate posts
- Verify the post exists and content matches after publishing
- Never interpret "draft" as "publish"
- Fail with VerificationError (non-retryable) if verification fails

## Examples
- "Publish the approved AI engineering summary to LinkedIn"

## Failure Modes
- No approval → raise ApprovalRequiredError (non-retryable)
- Duplicate detected → return existing post details, do not re-publish
- API error → raise ToolError (retryable with backoff, max 3 attempts)
- Verification fails → raise VerificationError, surface to user
