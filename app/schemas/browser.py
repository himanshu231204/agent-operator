"""Browser action/result schemas (PROJECT.md section 12)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

BrowserActionType = Literal[
    "navigate",
    "inspect",
    "click",
    "type",
    "select",
    "scroll",
    "wait",
    "extract",
    "screenshot",
    "download",
    "new_tab",
    "switch_tab",
    "list_tabs",
]

SelectorStrategy = Literal[
    "aria_role",
    "label",
    "test_attribute",
    "css",
    "text",
    "xpath",
    "coordinates",
]


class BrowserActionResult(BaseModel):
    success: bool
    action: BrowserActionType
    target: str | None = None
    url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class BrowserSessionRead(BaseModel):
    id: str
    status: Literal["open", "closed"]
    current_url: str | None = None
