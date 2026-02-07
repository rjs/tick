# A5 Spike: LLM Input Handler

## Context

A5 needs to take natural language commands from a TUI input field and produce structured tool calls (`add_locale`, `remove_locale`, `set_time_window`). Also handles locale name → IANA identifier resolution (per A2 spike findings).

## Goal

Identify the LLM runtime, model, tool-call protocol, and expected latency for the command input loop.

## Questions

| # | Question | Answer |
|---|----------|--------|
| **A5-Q1** | What local LLM runtimes are available? | **Ollama** is the clear winner for a TUI app: `brew install ollama`, daemon process, OpenAI-compatible API, native tool calling, first-class Python library. Alternatives: llama.cpp (more control, harder to set up), MLX (fastest on Apple Silicon but no tool calling abstraction), LM Studio (GUI-oriented). |
| **A5-Q2** | What's the smallest model that can reliably handle this? | **Qwen2.5-3B-Instruct** — 100% tool calling accuracy in Docker evaluation, ~2GB quantized. **Qwen3-1.7B** — nearly as capable, faster. For our constrained task (3 tools, simple args), even 1.5B may work. |
| **A5-Q3** | What tool-call protocols exist? | **Ollama native tool calling** (recommended) — define Python functions with type annotations, Ollama auto-generates JSON schema, returns structured `tool_calls` in response. Also: JSON mode, prompt engineering, GBNF grammars. |
| **A5-Q4** | What's the latency? | Cold start: 15-45s (avoidable — keep model loaded). With model loaded: **1-2s total** on M1, **0.5-1s** on M3 Pro/Max for a 30-token tool call response. TTFT dominates, not generation speed. |
| **A5-Q5** | Best language/library to call Ollama? | **Python `ollama` package** — `pip install ollama`, auto-schema from functions, sync/async. Also works via `openai` library pointed at localhost:11434. |
| **A5-Q6** | Could we skip the LLM entirely? | **Partially.** Regex handles simple commands (`add Detroit`, `today`, `feb 12`) at <1ms. But locale name → IANA resolution ("Brasil" → `America/Sao_Paulo`) and compound commands ("show me times feb 12 in brasil") need either an LLM or a large curated lookup table. |

## Findings

### Recommended Stack

- **Runtime:** Ollama
- **Model:** `qwen2.5:3b` (safest) or `qwen3:1.7b` (faster)
- **Protocol:** Ollama native tool calling
- **Library:** Python `ollama` package
- **Latency:** 1-2s per command (model pre-loaded)

### Example Code

```python
import ollama

def add_locale(name: str, iana_tz: str) -> str:
    """Add a locale to the display.
    Args:
        name: Display name (e.g. "Detroit")
        iana_tz: IANA timezone identifier (e.g. "America/Detroit")
    """
    pass

def remove_locale(name: str) -> str:
    """Remove a locale from the display.
    Args:
        name: Display name of the locale to remove
    """
    pass

def set_time_window(date: str) -> str:
    """Set the date to display times for.
    Args:
        date: ISO date string (YYYY-MM-DD)
    """
    pass

response = ollama.chat(
    'qwen2.5:3b',
    messages=[
        {'role': 'system', 'content': 'Parse user commands into tool calls. Resolve locale names to IANA timezone identifiers.'},
        {'role': 'user', 'content': 'show me times feb 12 in brasil'}
    ],
    tools=[add_locale, remove_locale, set_time_window],
)

for tool in response.message.tool_calls or []:
    print(f"{tool.function.name}({tool.function.arguments})")
# → set_time_window({'date': '2026-02-12'})
# → add_locale({'name': 'Brasil', 'iana_tz': 'America/Sao_Paulo'})
```

### Architecture Insight: Hybrid Parser

The spike revealed an interesting option — a layered approach:

1. **Regex parser** — handles simple unambiguous commands at <1ms (`add Detroit`, `today`, `feb 12`)
2. **LLM** — handles natural language, compound commands, locale resolution at 1-2s
3. **Fallback** — if Ollama not installed, ask user to be more specific

This means the LLM is optional for basic usage but required for the natural language experience described in R5.

## Conclusion

**A5 resolves to: Ollama + Qwen2.5-3B + native tool calling via Python `ollama` library.**

This also implies the TUI language is **Python** (best Ollama library support, `zoneinfo` stdlib for A2, rich TUI frameworks like Textual/Rich).

The hybrid parser is a nice-to-have but not essential for V1 — start with LLM-only, add regex fast-path later if latency matters.
