from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS, SEARCH_DELAY_SECONDS, USER_AGENT

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})
ROBOTS_CACHE: dict[str, RobotFileParser | None] = {}


def _sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def get_robots_parser(url: str) -> RobotFileParser | None:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url in ROBOTS_CACHE:
        return ROBOTS_CACHE[robots_url]
    parser = RobotFileParser()
    try:
        response = SESSION.get(robots_url, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.ok:
            parser.parse(response.text.splitlines())
            ROBOTS_CACHE[robots_url] = parser
            return parser
    except requests.RequestException:
        pass
    ROBOTS_CACHE[robots_url] = None
    return None


def can_fetch_url(url: str, user_agent: str = USER_AGENT) -> bool:
    parser = get_robots_parser(url)
    if parser is None:
        return True
    return parser.can_fetch(user_agent, url)


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
def fetch_url(url: str, accept: str = "*/*") -> requests.Response:
    _sleep(REQUEST_DELAY_SECONDS)
    response = SESSION.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response


def call_tavily_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    _sleep(SEARCH_DELAY_SECONDS)
    response = SESSION.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": max_results,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("results", [])


def call_serpapi_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []
    _sleep(SEARCH_DELAY_SECONDS)
    response = SESSION.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google",
            "q": query,
            "num": max_results,
            "api_key": api_key,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("organic_results", [])
