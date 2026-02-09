from datetime import date

import ollama


class OllamaError(Exception):
    """Raised when the Ollama service is unavailable or returns an error."""


MODEL = "qwen2.5:3b"

SYSTEM_PROMPT_TEMPLATE = """\
You are a timezone assistant. Parse the user's command into tool calls.

The current year is {year}.

Rules:
- When calling add_locale, you MUST provide BOTH the "name" and "iana_tz" arguments. Never omit iana_tz.
- Resolve locale names to IANA timezone identifiers. Examples:
  "Brasil" → name="Brasil", iana_tz="America/Sao_Paulo"
  "Tokyo" → name="Tokyo", iana_tz="Asia/Tokyo"
  "London" → name="London", iana_tz="Europe/London"
  "New York" → name="New York", iana_tz="America/New_York"
  "Detroit" → name="Detroit", iana_tz="America/Detroit"
  "Paris" → name="Paris", iana_tz="Europe/Paris"
  "Sydney" → name="Sydney", iana_tz="Australia/Sydney"
- For dates, convert to ISO 8601 format (YYYY-MM-DD). Use {year} as the year when not specified.
- Use the "after" parameter on add_locale to control position. If "after" is omitted, the locale is appended at the end.
- To move an existing locale, call add_locale with its current iana_tz and the desired "after" value.
- To place a locale first (before all others), set after to "FIRST".
- Examples:
  "add Tokyo" → add_locale(name="Tokyo", iana_tz="Asia/Tokyo")
  "add Tokyo after Detroit" → add_locale(name="Tokyo", iana_tz="Asia/Tokyo", after="Detroit")
  "move London to first" → add_locale(name="London", iana_tz="Europe/London", after="FIRST")
  "move London after Tokyo" → add_locale(name="London", iana_tz="Europe/London", after="Tokyo")
- A single command may require multiple tool calls (e.g. "feb 12 in Brasil" → set_time_window + add_locale).
- Only use the provided tools. Do not output plain text.
"""


def add_locale(name: str, iana_tz: str, after: str | None = None) -> None:
    """Add a new locale column, or reposition an existing one.

    Args:
        name: Display name for the locale (e.g. "Brasil", "Tokyo").
        iana_tz: IANA timezone identifier (e.g. "America/Sao_Paulo", "Asia/Tokyo").
        after: Place this locale after the named locale. Omit to append at end.
    """


def remove_locale(name: str) -> None:
    """Remove a locale column from the timezone table.

    Args:
        name: Display name of the locale to remove (e.g. "London").
    """


def set_time_window(date: str) -> None:
    """Change the date shown in the timezone table.

    Args:
        date: ISO 8601 date string (e.g. "2026-02-12").
    """


TOOLS = [add_locale, remove_locale, set_time_window]


def send_command(user_input: str) -> list[dict]:
    """Send a natural language command to the LLM and return parsed tool calls.

    Returns a list of dicts like: [{"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}}]
    Raises OllamaError on any communication failure.
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(year=date.today().year)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    try:
        response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
    except Exception as exc:
        raise OllamaError(str(exc)) from exc

    if not response.message.tool_calls:
        return []

    return [
        {
            "name": tc.function.name,
            "arguments": dict(tc.function.arguments),
        }
        for tc in response.message.tool_calls
    ]
