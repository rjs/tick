import json
import urllib.parse
import urllib.request
from urllib.error import URLError


def lookup_timezone(name: str) -> str | None:
    """Look up an IANA timezone for a place name via Open-Meteo geocoding API."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(name)}&count=1"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        return data["results"][0]["timezone"]
    except (URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError):
        return None
