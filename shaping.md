# Tick — Shaping

A TUI app that shows a table of hours across time zones, with an LLM-driven input for modifying the view.

---

## Frame

### Problem

- Coordinating across time zones is mentally taxing — you have to look up offsets, do math, and remember DST rules
- Time zone offset data can be stale if hardcoded (DST changes, political changes to tz rules)
- Existing tools don't let you naturally say "show me Feb 12 in Brasil" — they require manual configuration

### Outcome

- User sees a clear hour-by-hour table across multiple time zones at a glance
- Time zone data is always accurate (IANA tz database via local library, DST-aware)
- User can naturally instruct the app via text to add/remove locales and change the time window

---

## Requirements (R)

| ID | Requirement | Status |
|----|-------------|--------|
| R0 | Show a table: rows = hours, columns = locales, cells = local time | Core goal |
| R1 | Time zone offsets and DST rules must be accurate (use IANA tz database via local library) | Must-have |
| R2 | Accept locale names in natural form (e.g. "Detroit", "Brasil", "Poland") and resolve to tz offsets | Must-have |
| R3 | Support a configurable list of default time zones that are always loaded | Must-have |
| R4 | Default time window is "today" — the next 12 hours from now | Must-have |
| R5 | LLM-driven input field at the bottom of the TUI for natural language commands | Must-have |
| R6 | LLM can add/remove locale columns via tool calls | Must-have |
| R7 | LLM can change the time window (e.g. "today", "feb 12", "next tuesday") via tool calls | Must-have |
| R8 | Screen reloads/refreshes to reflect changes after LLM commands | Must-have |
| R9 | Runs as a TUI (terminal UI) | Must-have |
| R10 | Uses a local LLM (simple, lightweight) | Must-have |
| R11 | A single input command can combine actions — change time window and add/remove locales together (e.g. "feb 12 in brasil") | Must-have |

---

## A: Python TUI with Ollama-driven tz resolution + local tz library

LLM does double duty: handles natural language commands AND resolves locale names to IANA identifiers. Local tz library handles all time computation. Python + Textual for the TUI, Ollama + Qwen2.5-3B for the LLM.

| Part | Mechanism | Flag |
|------|-----------|:----:|
| **A1** | **TUI shell** — Textual app with three regions: a `Label` (top) showing the current date ("Feb 7, 2026"), a `DataTable` (middle) showing the hour grid, and an `Input` (bottom) for typing commands. The date label is always visible so the user sees which day the table represents. App holds state: `locales: list[{name, iana_tz}]`, `time_window: date`, `hours: range`. On state change, updates date label and rebuilds table via A3. | |
| **A2** | **Local tz library** — `zoneinfo.ZoneInfo(iana_tz)` creates timezone objects. `datetime.now(tz)` and `datetime(y,m,d,h, tzinfo=tz)` compute local times. `zoneinfo.available_timezones()` provides the ~590 valid IANA identifiers for validation. | |
| **A3** | **Hour table builder** — Iterates `hours` range for `time_window` date. For each hour, creates a UTC datetime, converts to each locale's timezone via `dt.astimezone(tz)`, formats as `"3:00 PM"`. Returns list of rows, each row is a list of formatted time strings. Columns are locale names. | |
| **A4** | **Default config** — `config.json` or `DEFAULTS` dict mapping display names to IANA identifiers, e.g. `{"Detroit": "America/Detroit", "London": "Europe/London"}`. Loaded on startup to populate initial `locales` state. | |
| **A5** | **LLM input handler** — On `Input.Submitted`, sends user text to `ollama.chat('qwen2.5:3b', messages=[system_prompt, user_msg], tools=[add_locale, remove_locale, set_time_window])`. System prompt instructs: "Parse commands into tool calls. Resolve locale names to IANA identifiers." Returns `response.message.tool_calls` list to A6. Async call so TUI stays responsive (~1-2s). | |
| **A6** | **Tool executor** — Loops over tool calls from A5. `add_locale(name, iana_tz)`: validates `iana_tz in available_timezones()`, appends to `locales`. `remove_locale(name)`: removes matching entry from `locales`. `set_time_window(date)`: parses ISO date string, updates `time_window`. After all calls processed, triggers A1 re-render. If `iana_tz` validation fails, falls back to Open-Meteo geocoding API (`geocoding-api.open-meteo.com/v1/search?name={name}&count=1` → `results[0].timezone`). | |

---

## Fit Check (R × A)

| Req | Requirement | Status | A |
|-----|-------------|--------|---|
| R0 | Show a table: rows = hours, columns = locales, cells = local time | Core goal | ✅ |
| R1 | Time zone offsets and DST rules must be accurate (use IANA tz database via local library) | Must-have | ✅ |
| R2 | Accept locale names in natural form (e.g. "Detroit", "Brasil", "Poland") and resolve to tz offsets | Must-have | ✅ |
| R3 | Support a configurable list of default time zones that are always loaded | Must-have | ✅ |
| R4 | Default time window is "today" — the next 12 hours from now | Must-have | ✅ |
| R5 | LLM-driven input field at the bottom of the TUI for natural language commands | Must-have | ✅ |
| R6 | LLM can add/remove locale columns via tool calls | Must-have | ✅ |
| R7 | LLM can change the time window (e.g. "today", "feb 12", "next tuesday") via tool calls | Must-have | ✅ |
| R8 | Screen reloads/refreshes to reflect changes after LLM commands | Must-have | ✅ |
| R9 | Runs as a TUI (terminal UI) | Must-have | ✅ |
| R10 | Uses a local LLM (simple, lightweight) | Must-have | ✅ |

| R11 | A single input command can combine actions — change time window and add/remove locales together (e.g. "feb 12 in brasil") | Must-have | ✅ |

All requirements pass. No flagged unknowns remain.

---

## Decisions needed

1. ~~**Language/framework for TUI**~~ — **Resolved.** Python + Textual.

2. ~~**Time zone data source (A2)**~~ — **Resolved.** LLM resolves names → IANA identifiers. Local `zoneinfo` computes times. Open-Meteo geocoding as fallback.

3. ~~**Local LLM runtime (A5)**~~ — **Resolved.** Ollama + `qwen2.5:3b` (~2GB). Python `ollama` library.

4. ~~**Tool call protocol (A5/A6)**~~ — **Resolved.** Ollama native tool calling. Define Python functions with type annotations, Ollama auto-generates JSON schema, returns structured `tool_calls` in response.
