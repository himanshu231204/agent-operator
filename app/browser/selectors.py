"""Resilient selector strategy (PROJECT.md section 12, AGENTS.md rules 77-84).

Preferred order: ARIA role + accessible name, label, stable test/data
attribute, semantic CSS, text, XPath, coordinates (last resort).
"""

from __future__ import annotations

from playwright.async_api import Locator, Page

from app.schemas.browser import SelectorStrategy

#: Order agents should try selector strategies in, most resilient first.
STRATEGY_PRIORITY: tuple[SelectorStrategy, ...] = (
    "aria_role",
    "label",
    "test_attribute",
    "css",
    "text",
    "xpath",
    "coordinates",
)


def resolve_locator(
    page: Page, strategy: SelectorStrategy, value: str, *, role: str | None = None
) -> Locator:
    """Build a Playwright ``Locator`` for the given strategy.

    ``coordinates`` has no locator equivalent; callers must use
    ``page.mouse`` directly and should treat that as a last resort.
    """

    match strategy:
        case "aria_role":
            if role is None:
                raise ValueError("aria_role strategy requires a role")
            return page.get_by_role(role, name=value)  # type: ignore[arg-type]
        case "label":
            return page.get_by_label(value)
        case "test_attribute":
            return page.locator(f"[data-testid='{value}']")
        case "css":
            return page.locator(value)
        case "text":
            return page.get_by_text(value)
        case "xpath":
            return page.locator(f"xpath={value}")
        case "coordinates":
            raise ValueError("coordinates strategy has no Locator equivalent")
    raise ValueError(f"Unknown selector strategy: {strategy!r}")
