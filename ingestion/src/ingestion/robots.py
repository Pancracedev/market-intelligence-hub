"""robots.txt compliance check for generic, user-supplied URLs (price watchers)."""

from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

_CACHE_TTL_SECONDS = 3600
_cache: dict[str, tuple[float, RobotFileParser]] = {}


class RobotsDisallowedError(RuntimeError):
    """Raised when robots.txt disallows fetching the given URL for our User-Agent."""


def _get_parser(domain_root: str, user_agent: str) -> RobotFileParser:
    now = time.time()
    cached = _cache.get(domain_root)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    parser = RobotFileParser()
    parser.set_url(f"{domain_root}/robots.txt")
    try:
        # Fetch via `requests` (not RobotFileParser.read()'s own urllib call) so this
        # goes through the same HTTP stack as the rest of the codebase - consistent
        # timeouts/User-Agent, and mockable in tests.
        response = requests.get(f"{domain_root}/robots.txt", headers={"User-Agent": user_agent}, timeout=10)
        if response.status_code >= 400:
            parser.parse([])
        else:
            parser.parse(response.text.splitlines())
    except requests.RequestException:
        # Unreachable robots.txt: treat as "allow all" rather than blocking scrapes on
        # transient network issues unrelated to the target page itself.
        parser.parse([])
    _cache[domain_root] = (now, parser)
    return parser


def is_allowed(url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    parser = _get_parser(domain_root, user_agent)
    return parser.can_fetch(user_agent, url)


def check_allowed(url: str, user_agent: str) -> None:
    if not is_allowed(url, user_agent):
        raise RobotsDisallowedError(f"robots.txt disallows fetching {url} for User-Agent '{user_agent}'")
