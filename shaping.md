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

## Detail A: Breadboard

### Places

| # | Place | Description |
|---|-------|-------------|
| P1 | TUI Main | The single-screen TUI: date label, hour table, command input |
| P2 | Ollama | Local LLM service (external process) |
| P3 | Open-Meteo | Geocoding fallback API (external) |

### UI Affordances

| # | Place | Component | Affordance | Control | Wires Out | Returns To |
|---|-------|-----------|------------|---------|-----------|------------|
| U1 | P1 | header | date label ("Feb 7, 2026") | render | — | — |
| U2 | P1 | table | column headers (locale names) | render | — | — |
| U3 | P1 | table | hour rows (formatted local times) | render | — | — |
| U4 | P1 | footer | command input | type + submit | → N1 | — |
| U5 | P1 | footer | loading indicator ("Thinking...") | render | — | — |

### Code Affordances

| # | Place | Component | Affordance | Control | Wires Out | Returns To |
|---|-------|-----------|------------|---------|-----------|------------|
| N1 | P1 | app | `on_input_submitted()` | call | → N2, → S3 | — |
| N2 | P2 | ollama | `ollama.chat(model, messages, tools)` | call | — | → N3 |
| N3 | P1 | app | `execute_tool_calls(tool_calls)` | call | → N4, → N5, → N6 | → N7 |
| N4 | P1 | app | `add_locale(name, iana_tz)` | call | → N8 | → S1 |
| N5 | P1 | app | `remove_locale(name)` | call | — | → S1 |
| N6 | P1 | app | `set_time_window(date)` | call | — | → S2 |
| N7 | P1 | app | `rebuild_table()` | call | → N9 | → U1, → U2, → U3 |
| N8 | P1 | app | `validate_iana_tz(iana_tz)` | call | → N10 | → N4 |
| N9 | P1 | app | `compute_hours(locales, time_window)` | call | — | → N7 |
| N10 | P3 | open-meteo | `geocoding-api.open-meteo.com/v1/search` | call | — | → N8 |
| N11 | P1 | app | `load_defaults()` | call | — | → S1, → S2, → N7 |

### Data Stores

| # | Place | Store | Description |
|---|-------|-------|-------------|
| S1 | P1 | `locales` | `list[{name: str, iana_tz: str}]` — active locale columns |
| S2 | P1 | `time_window` | `date` — the day being displayed |
| S3 | P1 | `loading` | `bool` — whether LLM call is in progress |

### Wiring Narrative

**Startup flow:** `N11 load_defaults()` reads config → writes default locales to `S1`, today's date to `S2` → calls `N7 rebuild_table()` → `N9 compute_hours()` uses `zoneinfo` to convert each hour to each locale's timezone → `N7` updates `U1` (date label), `U2` (column headers), `U3` (hour rows).

**Command flow:** User types in `U4` → submit fires `N1` → sets `S3` loading (shows `U5`) → calls `N2` Ollama with tools → LLM returns tool calls → `N3` loops them: `N4` adds locale (validates via `N8`, falls back to `N10`), `N5` removes locale, `N6` sets date → after all calls, `N3` calls `N7` rebuild → table updates.

### Mermaid

```mermaid
flowchart TB
    subgraph P1["P1: TUI Main"]
        subgraph header["header"]
            U1["U1: date label"]
        end

        subgraph table["table"]
            U2["U2: column headers"]
            U3["U3: hour rows"]
        end

        subgraph footer["footer"]
            U4["U4: command input"]
            U5["U5: loading indicator"]
        end

        S1["S1: locales"]
        S2["S2: time_window"]
        S3["S3: loading"]

        N1["N1: on_input_submitted()"]
        N3["N3: execute_tool_calls()"]
        N4["N4: add_locale()"]
        N5["N5: remove_locale()"]
        N6["N6: set_time_window()"]
        N7["N7: rebuild_table()"]
        N8["N8: validate_iana_tz()"]
        N9["N9: compute_hours()"]
        N11["N11: load_defaults()"]
    end

    subgraph P2["P2: Ollama"]
        N2["N2: ollama.chat()"]
    end

    subgraph P3["P3: Open-Meteo"]
        N10["N10: geocoding API"]
    end

    %% Startup
    N11 --> S1
    N11 --> S2
    N11 --> N7

    %% Command flow
    U4 -->|submit| N1
    N1 --> S3
    S3 -.-> U5
    N1 --> N2
    N2 -.-> N3

    %% Tool execution
    N3 --> N4
    N3 --> N5
    N3 --> N6
    N4 --> N8
    N8 --> N10
    N10 -.-> N8
    N8 -.-> N4
    N4 --> S1
    N5 --> S1
    N6 --> S2

    %% Rebuild
    N3 --> N7
    N7 --> N9
    S1 -.-> N9
    S2 -.-> N9
    N9 -.-> N7
    N7 --> U1
    N7 --> U2
    N7 --> U3

    classDef ui fill:#ffb6c1,stroke:#d87093,color:#000
    classDef nonui fill:#d3d3d3,stroke:#808080,color:#000
    classDef store fill:#e6e6fa,stroke:#9370db,color:#000

    class U1,U2,U3,U4,U5 ui
    class N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11 nonui
    class S1,S2,S3 store
```

**Legend:**
- **Pink nodes (U)** = UI affordances (things users see/interact with)
- **Grey nodes (N)** = Code affordances (methods, handlers, services)
- **Lavender nodes (S)** = Data stores (state)
- **Solid lines** = Wires Out (calls, triggers, writes)
- **Dashed lines** = Returns To (return values, data reads)

---

## Slices

### Slice Summary

| # | Slice | Parts | Demo |
|---|-------|-------|------|
| V1 | Table with defaults | A1, A2, A3, A4 | "App launches, shows today's hours across default time zones" |
| V2 | LLM commands work | A5, A6 | "Type 'feb 12 in Brasil' — date changes, Brasil column appears" |

### V1: Table with defaults

| # | Component | Affordance | Control | Wires Out | Returns To |
|---|-----------|------------|---------|-----------|------------|
| U1 | header | date label ("Feb 7, 2026") | render | — | — |
| U2 | table | column headers (locale names) | render | — | — |
| U3 | table | hour rows (formatted local times) | render | — | — |
| N11 | app | `load_defaults()` | call | → S1, → S2, → N7 | — |
| N7 | app | `rebuild_table()` | call | → N9 | → U1, → U2, → U3 |
| N9 | app | `compute_hours(locales, time_window)` | call | — | → N7 |
| S1 | app | `locales` | store | — | → N9 |
| S2 | app | `time_window` | store | — | → N9 |

### V2: LLM commands work

| # | Component | Affordance | Control | Wires Out | Returns To |
|---|-----------|------------|---------|-----------|------------|
| U4 | footer | command input | type + submit | → N1 | — |
| U5 | footer | loading indicator ("Thinking...") | render | — | — |
| N1 | app | `on_input_submitted()` | call | → N2, → S3 | — |
| N2 | ollama | `ollama.chat(model, messages, tools)` | call | — | → N3 |
| N3 | app | `execute_tool_calls(tool_calls)` | call | → N4, → N5, → N6 | → N7 |
| N4 | app | `add_locale(name, iana_tz)` | call | → N8 | → S1 |
| N5 | app | `remove_locale(name)` | call | — | → S1 |
| N6 | app | `set_time_window(date)` | call | — | → S2 |
| N8 | app | `validate_iana_tz(iana_tz)` | call | → N10 | → N4 |
| N10 | open-meteo | geocoding API | call | — | → N8 |
| S3 | app | `loading` | store | — | → U5 |

### Sliced Breadboard

```mermaid
flowchart TB
    subgraph slice1["V1: TABLE WITH DEFAULTS"]
        subgraph header["header"]
            U1["U1: date label"]
        end
        subgraph table["table"]
            U2["U2: column headers"]
            U3["U3: hour rows"]
        end
        S1["S1: locales"]
        S2["S2: time_window"]
        N7["N7: rebuild_table()"]
        N9["N9: compute_hours()"]
        N11["N11: load_defaults()"]
    end

    subgraph slice2["V2: LLM COMMANDS WORK"]
        subgraph footer["footer"]
            U4["U4: command input"]
            U5["U5: loading indicator"]
        end
        S3["S3: loading"]
        N1["N1: on_input_submitted()"]
        N2["N2: ollama.chat()"]
        N3["N3: execute_tool_calls()"]
        N4["N4: add_locale()"]
        N5["N5: remove_locale()"]
        N6["N6: set_time_window()"]
        N8["N8: validate_iana_tz()"]
        N10["N10: geocoding API"]
    end

    slice1 ~~~ slice2

    %% Startup
    N11 --> S1
    N11 --> S2
    N11 --> N7

    %% Rebuild
    N7 --> N9
    S1 -.-> N9
    S2 -.-> N9
    N9 -.-> N7
    N7 --> U1
    N7 --> U2
    N7 --> U3

    %% Command flow
    U4 -->|submit| N1
    N1 --> S3
    S3 -.-> U5
    N1 --> N2
    N2 -.-> N3

    %% Tool execution
    N3 --> N4
    N3 --> N5
    N3 --> N6
    N4 --> N8
    N8 --> N10
    N10 -.-> N8
    N8 -.-> N4
    N4 --> S1
    N5 --> S1
    N6 --> S2

    %% Cross-slice: rebuild after commands
    N3 --> N7

    style slice1 fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style slice2 fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style header fill:transparent,stroke:#888,stroke-width:1px
    style table fill:transparent,stroke:#888,stroke-width:1px
    style footer fill:transparent,stroke:#888,stroke-width:1px

    classDef ui fill:#ffb6c1,stroke:#d87093,color:#000
    classDef nonui fill:#d3d3d3,stroke:#808080,color:#000
    classDef store fill:#e6e6fa,stroke:#9370db,color:#000

    class U1,U2,U3,U4,U5 ui
    class N1,N2,N3,N4,N5,N6,N7,N8,N9,N10,N11 nonui
    class S1,S2,S3 store
```

**Legend:**
- **Green boundary (V1)** = Table with defaults — pure rendering, no external deps
- **Blue boundary (V2)** = LLM commands — Ollama input, tool execution, rebuild
- **Pink nodes (U)** = UI affordances
- **Grey nodes (N)** = Code affordances
- **Lavender nodes (S)** = Data stores
- **Solid lines** = Wires Out (calls, triggers, writes)
- **Dashed lines** = Returns To (return values, data reads)

---

## Decisions needed

1. ~~**Language/framework for TUI**~~ — **Resolved.** Python + Textual.

2. ~~**Time zone data source (A2)**~~ — **Resolved.** LLM resolves names → IANA identifiers. Local `zoneinfo` computes times. Open-Meteo geocoding as fallback.

3. ~~**Local LLM runtime (A5)**~~ — **Resolved.** Ollama + `qwen2.5:3b` (~2GB). Python `ollama` library.

4. ~~**Tool call protocol (A5/A6)**~~ — **Resolved.** Ollama native tool calling. Define Python functions with type annotations, Ollama auto-generates JSON schema, returns structured `tool_calls` in response.
