"""Web fetch tool (PROJECT.md section 8, phase 4).

Implements WebFetchTool — an SSRF-protected httpx-based HTTP fetcher
registered in the ToolRegistry so the research agent graph can fetch URLs
through the ToolExecutionEngine permission gate.

SSRF protection: resolves hostname to IPs and blocks all private/internal
ranges before making any network connection (AGENTS.md rules 168-169).
"""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions

_ALLOWED_SCHEMES = frozenset({"http", "https"})

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata endpoint
    ipaddress.ip_network("fc00::/7"),         # unique local IPv6
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
]

_MAX_CONTENT_CHARS = 50_000


def _guard_url(url: str) -> None:
    """Raise ToolError if *url* targets a private/internal address."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ToolError(
            f"URL scheme {parsed.scheme!r} is not allowed; only http and https are permitted",
            context={"url": url, "code": "ssrf_blocked"},
        )
    hostname = parsed.hostname
    if not hostname:
        raise ToolError("URL has no hostname", context={"url": url, "code": "ssrf_blocked"})

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ToolError(
            f"Could not resolve hostname {hostname!r}: {exc}",
            context={"url": url, "code": "dns_failed"},
        ) from exc

    for info in infos:
        addr_str = info[4][0]
        try:
            ip = ipaddress.ip_address(addr_str)
        except ValueError:
            continue
        for net in _PRIVATE_NETWORKS:
            if ip in net:
                raise ToolError(
                    f"Fetch to private/internal address {addr_str!r} is blocked (SSRF protection)",
                    context={"url": url, "addr": addr_str, "code": "ssrf_blocked"},
                )


def _extract_text(html: str, content_type: str) -> str:
    """Strip HTML tags and truncate to _MAX_CONTENT_CHARS."""
    if "text/html" in content_type:
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s{2,}", " ", html).strip()
    return html[:_MAX_CONTENT_CHARS]


class WebFetchInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)


class WebFetchOutput(BaseModel):
    content: str
    status_code: int
    content_type: str
    url: str


class WebFetchTool(BaseTool[WebFetchInput, WebFetchOutput]):
    name: ClassVar[str] = "web_fetch"
    description: ClassVar[str] = (
        "Fetch the text content of a web page. Use after web_search to read the full "
        "content of a specific page. Extracts readable text from HTML. "
        "Never fetches private, internal, or cloud-metadata addresses."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        requires_authentication=False,
    )
    timeout_seconds: ClassVar[float] = 30.0

    async def execute(self, tool_input: WebFetchInput) -> WebFetchOutput:
        _guard_url(tool_input.url)

        try:
            import httpx
        except ImportError as exc:
            raise ToolError(
                "httpx is required for web fetch — add it to pyproject.toml dependencies",
                context={"tool_name": self.name},
            ) from exc

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=tool_input.timeout_seconds,
            ) as client:
                response = await client.get(
                    tool_input.url,
                    headers={"User-Agent": "AgentOperator/1.0 (research-bot)"},
                )
        except httpx.TimeoutException as exc:
            raise ToolError(
                f"Request timed out after {tool_input.timeout_seconds}s: {tool_input.url}",
                context={"url": tool_input.url},
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError(
                f"HTTP request failed: {exc}",
                context={"url": tool_input.url},
            ) from exc

        content_type = response.headers.get("content-type", "text/plain")
        text = _extract_text(response.text, content_type)

        return WebFetchOutput(
            content=text,
            status_code=response.status_code,
            content_type=content_type,
            url=str(response.url),
        )
