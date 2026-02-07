# A2 Spike: Time Zone Resolver

## Context

A2 needs to take natural locale names (e.g. "Detroit", "Brasil", "Poland") and resolve them to IANA timezone identifiers with correct UTC offsets. We need to know what mechanism to use.

## Goal

Identify how to reliably map natural names → IANA tz identifiers → accurate local times, and whether we need an internet API at all.

## Questions

| # | Question | Answer |
|---|----------|--------|
| **A2-Q1** | What free public tz APIs exist that accept natural city/country names? | Almost none. WorldTimeAPI (unreliable, IANA-only). TimeAPI.io (IANA or coords only, no key). API Ninjas and IPGeolocation.io accept city names but require API keys and paid tiers. |
| **A2-Q2** | Can we do geocoding → timezone in one step? | **Yes. Open-Meteo geocoding API** (`geocoding-api.open-meteo.com/v1/search?name=Detroit&count=1`) returns IANA timezone directly in the response. Free, no API key. |
| **A2-Q3** | Can we skip internet APIs entirely and use local tz data? | **Yes** — Python `zoneinfo` (stdlib 3.9+) and Rust `chrono-tz` both have full IANA databases locally. The only problem is mapping natural names to IANA identifiers. |
| **A2-Q4** | Can the LLM itself resolve natural names to IANA identifiers? | **Yes** — LLMs reliably map "Detroit" → `America/Detroit`, "Brasil" → `America/Sao_Paulo`, "Poland" → `Europe/Warsaw`. Validate against known identifier set. Handles informal inputs ("Eastern time", "the UK", "CET") naturally. |
| **A2-Q5** | Are there gotchas with the LLM approach? | Possible hallucinated identifiers (mitigate: validate against `available_timezones()`). Ambiguous inputs like "Russia" or "Australia" (multiple zones — LLM can pick most populous or ask). |

## Findings

Three viable approaches emerged, in order of simplicity:

### Approach 1: LLM resolves name + local tz library (recommended)

Since the app already talks to an LLM (A5), add name resolution as a tool call:
- LLM returns IANA identifier as part of `add_locale` tool call
- Local `zoneinfo` (Python) or `chrono-tz` (Rust) computes offsets and times
- Validate returned identifier against known set
- **Zero additional APIs. Works offline after LLM step.**

### Approach 2: Open-Meteo geocoding as fallback

If LLM returns an invalid identifier, call:
```
GET https://geocoding-api.open-meteo.com/v1/search?name=Detroit&count=1
→ {"results": [{"timezone": "America/Detroit", ...}]}
```
Free, no key, returns IANA timezone directly.

### Approach 3: Full API approach (not recommended)

Chain geocoding API → tz API. More moving parts, no benefit over approaches 1–2.

## Conclusion

**A2 resolves to: LLM does name resolution → local tz library does time computation.**

The LLM already exists in the system (A5). Making it also resolve locale names to IANA identifiers collapses A2 into A5's responsibilities — the `add_locale` tool call includes the IANA identifier. Local `zoneinfo`/`chrono-tz` handles all offset math, DST, etc.

Open-Meteo geocoding is a good fallback if validation fails.

This means **R1 (fresh data from internet) needs re-examination** — the IANA database is local but updated with OS/package updates, not per-launch. The offsets are computed correctly for any date because DST rules are encoded in the database. "Freshness" comes from keeping the tz database updated, not from an API call.
