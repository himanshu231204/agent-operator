# Skill: Browser Control

## Purpose
Navigate the web using a real Chromium browser. Suitable for pages that
require JavaScript rendering or authenticated sessions.

## Inputs
```json
{
  "instruction": "string — what to do in the browser (natural language)",
  "start_url": "string (optional) — URL to open first",
  "session_id": "string (optional) — resume an existing browser session"
}
```

## Outputs
```json
{
  "result": "string — extracted information or action outcome",
  "final_url": "string",
  "screenshot_path": "string (optional)",
  "actions_taken": ["description of each browser action"]
}
```

## Required Tools
- PlaywrightBrowserToolkit (navigate, click, type, extract_text, screenshot, ...)

## Required Permissions
- LOW risk for read-only actions (navigate, inspect, extract, screenshot)
- MEDIUM risk for interactive actions (click, type, submit)
- No user approval required for read-only workflows

## Safety Constraints
- Never bypass authentication controls or defeat security measures
- Never evade CAPTCHA
- Never impersonate another person
- Never execute arbitrary downloaded code
- Prefer accessibility selectors over fragile CSS class names
- Isolate browser sessions between tasks/users

## Examples
- "Open the browser and find pricing for three competing SaaS products"
- "Navigate to the dashboard and extract the usage statistics"

## Failure Modes
- Browser crash → recover session and retry (BrowserError, retryable)
- Navigation timeout → raise BrowserError with retryable=True
- Element not found → try fallback selector strategy before failing
- Authentication expired → raise AuthenticationError (requires user)
