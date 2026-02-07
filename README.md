# Tick

A TUI app that shows a table of hours across time zones, with a natural language input for modifying the view.

Type "add Brasil" and a new column appears. Type "feb 12" and the date changes. Type "paris feb 18" and both happen at once.

This is the project for the case study [Shaping 0-1 with Claude Code](https://x.com/rjs/status/2020184079350563263). Built using [Claude Code](https://claude.com/claude-code) with [shaping skills](https://github.com/rjs/shaping-skills).

## How it works

- A [Textual](https://textual.textualize.io/) TUI renders an hour-by-hour table across time zones
- Time zone math uses Python's `zoneinfo` (IANA tz database, DST-aware)
- An input field at the bottom accepts natural language commands
- A local [Ollama](https://ollama.com) LLM (`qwen2.5:3b`) parses commands into tool calls: add/remove locales, change the date
- [Open-Meteo geocoding](https://open-meteo.com/) provides a fallback for timezone resolution

## Setup

Requires Python 3.14+, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com/download).

```
# Install dependencies
uv sync

# Pull the local LLM
ollama pull qwen2.5:3b

# Run
uv run tick
```

## Commands

Type into the input field at the bottom of the TUI:

| Command | What happens |
|---|---|
| `add Brasil` | Adds a Brasil column (America/Sao_Paulo) |
| `feb 12` | Changes the date to Feb 12 |
| `paris feb 18` | Adds Paris and changes date to Feb 18 |
| `remove London` | Removes the London column |

## How it was shaped

This project was shaped from scratch using Claude Code with [shaping skills](https://github.com/rjs/shaping-skills) that implement the methodology from [Shape Up](https://basecamp.com/shapeup). The full process is documented in the repo:

- `shaping.md` &mdash; Requirements, shape, fit checks, breadboard, and slices
- `spike-a2.md` &mdash; Spike on timezone API approaches
- `spike-a5.md` &mdash; Spike on local LLM integration

The workflow went like this:

1. **Described the idea** in plain language and asked Claude to separate problem from solution using the shaping skill
2. **Checked the fit** between requirements (R) and shape (A) to see what was solved and what wasn't
3. **Spiked unknowns** &mdash; discovered we didn't need a network API for timezones (local `zoneinfo` is sufficient), and chose Ollama with tool calling for the LLM
4. **Sketched the UI** in tldraw to make sure the date label was an explicit affordance
5. **Breadboarded** the system into UI affordances, code affordances, and wiring
6. **Sliced vertically** into two demoable scopes: static table first, then LLM commands
7. **Built and verified** each slice, testing end-to-end with real Ollama calls

No steps were skipped. The whole thing went from an empty directory to a working product.

## Tests

```
uv run pytest tests/ -v
```
