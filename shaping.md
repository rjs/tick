# Tick — Shaping

A TUI app that shows a table of hours across time zones, with an LLM-driven input for modifying the view.

---

## Frame

### Source

> I want to create a simple TUI app here. it should talk to the internet to get a reliable source of what the current time zone is in a specified locale. eg Detroit. or Brasil. or Poland. Then it should show a table of every hour for each of the locales that i ask. each locale is a column in the table, and the rows are hours in the day, and the local time then is in each cell.
>
> i should be able to specify a few default time zones that are always loaded.
>
> it's important that it fetches the data freshly every time it loads (so it is accurate), and it should default to a list of the hours in the current day. (eg the next 12 hrs).
>
> there should be an input field at the bottom where i can make request to a very simple local LLM to instruct the app to add/remove locales and or change the "time window" which is the day that we are looking at. via tool calls. so i could be able to say "today" or "feb 12" etc. "show me times feb 12 in brasil". and the screen will reload to show me the table with brasil included and the time window changed to feb 12 (of the current year).

### Problem

- Coordinating across time zones is mentally taxing — you have to look up offsets, do math, and remember DST rules
- Time zone offset data can be stale if hardcoded (DST changes, political changes to tz rules)
- Existing tools don't let you naturally say "show me Feb 12 in Brasil" — they require manual configuration

### Outcome

- User sees a clear hour-by-hour table across multiple time zones at a glance
- Time zone data is always fresh and accurate (fetched from the internet on each load)
- User can naturally instruct the app via text to add/remove locales and change the time window

---

## Requirements (R)

| ID | Requirement | Status |
|----|-------------|--------|
| R0 | Show a table: rows = hours, columns = locales, cells = local time | Core goal |
| R1 | Fetch time zone data from the internet on every app load (no stale/hardcoded offsets) | Must-have |
| R2 | Accept locale names in natural form (e.g. "Detroit", "Brasil", "Poland") and resolve to tz offsets | Must-have |
| R3 | Support a configurable list of default time zones that are always loaded | Must-have |
| R4 | Default time window is "today" — the next 12 hours from now | Must-have |
| R5 | LLM-driven input field at the bottom of the TUI for natural language commands | Must-have |
| R6 | LLM can add/remove locale columns via tool calls | Must-have |
| R7 | LLM can change the time window (e.g. "today", "feb 12", "next tuesday") via tool calls | Must-have |
| R8 | Screen reloads/refreshes to reflect changes after LLM commands | Must-have |
| R9 | Runs as a TUI (terminal UI) | Must-have |
| R10 | Uses a local LLM (simple, lightweight) | Must-have |

---

## A: Single-shape TUI with internet tz lookup + local LLM input

This is the shape you described. Let me break it into parts.

| Part | Mechanism | Flag |
|------|-----------|:----:|
| **A1** | **TUI shell** — Terminal UI framework renders a table + input field layout | |
| **A2** | **Time zone resolver** — Takes natural locale names (e.g. "Detroit"), calls an internet API to resolve to IANA tz identifier and current UTC offset | ⚠️ |
| **A3** | **Hour table builder** — Given a list of tz offsets and a time window (date + hour range), computes the local time for each hour in each zone and produces the table data | |
| **A4** | **Default config** — A config file or constant defining the default locale list loaded on startup | |
| **A5** | **LLM input handler** — Captures text from the input field, sends to a local LLM with tool definitions for `add_locale`, `remove_locale`, `set_time_window` | ⚠️ |
| **A6** | **Tool executor** — Receives tool calls from the LLM, mutates app state (locale list, time window), triggers re-render | |

### Open questions on flagged parts

**A2 — Time zone resolver (⚠️):** What internet source do we use? Options:
- A public tz API (e.g. WorldTimeAPI, TimeAPI.io, Google Time Zone API)
- A geocoding API to resolve "Detroit" → lat/lon, then a tz API to resolve lat/lon → tz
- Something simpler?

**A5 — LLM input handler (⚠️):** What local LLM setup? Options:
- Ollama running locally with a small model (e.g. llama3, phi3)
- llama.cpp directly
- Something else?

And: what tool-call protocol? (native function calling vs. structured output parsing)

---

## Fit Check (R × A)

| Req | Requirement | Status | A |
|-----|-------------|--------|---|
| R0 | Show a table: rows = hours, columns = locales, cells = local time | Core goal | ✅ |
| R1 | Fetch time zone data from the internet on every app load (no stale/hardcoded offsets) | Must-have | ❌ |
| R2 | Accept locale names in natural form (e.g. "Detroit", "Brasil", "Poland") and resolve to tz offsets | Must-have | ❌ |
| R3 | Support a configurable list of default time zones that are always loaded | Must-have | ✅ |
| R4 | Default time window is "today" — the next 12 hours from now | Must-have | ✅ |
| R5 | LLM-driven input field at the bottom of the TUI for natural language commands | Must-have | ✅ |
| R6 | LLM can add/remove locale columns via tool calls | Must-have | ❌ |
| R7 | LLM can change the time window (e.g. "today", "feb 12", "next tuesday") via tool calls | Must-have | ❌ |
| R8 | Screen reloads/refreshes to reflect changes after LLM commands | Must-have | ✅ |
| R9 | Runs as a TUI (terminal UI) | Must-have | ✅ |
| R10 | Uses a local LLM (simple, lightweight) | Must-have | ❌ |

**Notes:**
- R1 fails: A2 (tz resolver) is flagged — we don't yet know which API or approach
- R2 fails: A2 (tz resolver) is flagged — natural name resolution mechanism unknown
- R6 fails: A5 (LLM input) is flagged — tool call protocol undecided
- R7 fails: A5 (LLM input) is flagged — tool call protocol undecided
- R10 fails: A5 (LLM input) is flagged — local LLM runtime undecided

---

## Decisions needed

1. **Language/framework for TUI** — What language do you want to build this in? (Python + Textual? Go + Bubble Tea? Rust + Ratatui? Something else?)

2. **Time zone data source (A2)** — How should we resolve "Detroit" → timezone? Need to pick an API.

3. **Local LLM runtime (A5)** — Ollama? llama.cpp? What model?

4. **Tool call protocol (A5/A6)** — How does the LLM communicate structured commands back to the app?
