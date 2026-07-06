---
name: telegram-bot-audit
description: Methodology for auditing and debugging Telegram bots built with python-telegram-bot, especially ones deployed on Render with multiple services (web/worker/cron) and Supabase/JSON storage. Use this whenever the user asks to audit, review, find bugs in, or fact-check an audit of a Telegram bot codebase — including this project's own bots (expat_rent_bot / euro_rent_bot, Kuper-666 GitHub account). Also use when the user pastes in a bug report or AI-generated audit document and asks whether it's accurate, when inline keyboard buttons "don't work," when deep links or referral links silently fail, when PDF generation crashes, or when something behaves differently in production than expected. Push hard to use this skill instead of just reading code and guessing — this project's bugs are consistently the kind that only show up when code actually runs, not when read.
---

# Telegram Bot Audit

Methodology distilled from an extended audit/debugging session on `expat_rent_bot`
(GitHub: `Kuper-666/euro_rent_bot`, formerly `EuroRentAIBot`). The single biggest
lesson from that session: **reading code and pattern-matching finds maybe half
the real bugs, and invents a bunch of fake ones.** Every confirmed bug in that
session was confirmed by actually executing the real function with real
(mocked) inputs. Every fake bug (about half of an external AI audit's
"critical" findings) was fake specifically because nobody ran the code before
writing it down.

## Core principle: verify by execution, not by reading

For every suspected bug, before reporting it as real:
1. Write a small script that imports the actual project module and calls the
   actual function/handler with realistic mock inputs (`unittest.mock.MagicMock`/
   `AsyncMock` for Telegram `Update`/`Context` objects).
2. Run it. Watch it actually fail (or not).
3. Only then report it as confirmed — and say so ("подтверждено практическим
   тестом", not "похоже на баг").

This matters especially for:
- **Claims about Python runtime behavior** ("this will throw X exception") —
  test it. `urllib.parse.unquote()` on garbage input, calling async methods on
  a bare unconfigured `Bot()` object, etc. all turned out to behave better than
  assumed when actually tested.
- **Claims from other audits** (AI-generated or otherwise) — treat every "BUG-NNN"
  entry as a hypothesis to check, not a fact. In the reference audit fact-checked
  during this project, roughly half of the "critical" bugs did not reproduce
  (wrong claims about `asyncio.run()` threading, sync `Bot()` objects needing
  an event loop, Dockerfile layer order, `unquote()` crashing) while some
  *unclaimed* bugs were far more severe than anything in the report (see below).

## Bug classes to specifically check for in this stack

These are the bug patterns that actually occurred, roughly in order of how
much damage they did:

### 1. Cross-service storage isolation (Render / multi-service deployments)
If `render.yaml` (or equivalent) defines separate services (web + worker +
cron jobs), **each has its own ephemeral filesystem**. A local JSON/SQLite
file written by one service is invisible to another, and cron-job services
get a *fresh* container on every scheduled run — so even a single service's
own local file resets on every run.
- Check: does every local file (`*.json`, `*.jsonl`, `*.sqlite3`) get written
  by one service and read by another? If yes, it's broken right now, silently.
- Check: does a cron-triggered service (posting, dedup, email digest) rely on
  local state to avoid repeating itself? It can't — state resets every run.
- Fix pattern used successfully here: move the specific piece of shared state
  to Supabase (or equivalent real DB), **with a local-file fallback for local
  dev** (see `rent_scanner/formatting.py`'s `create_url_token`/`resolve_url_token`
  for the reference implementation) — and log (don't silently swallow) any
  Supabase failure, or the fallback itself becomes an invisible failure mode.
- Test this with an actual end-to-end round trip: create the token/record via
  module A's function, resolve it via module B's function, assert the data
  matches — not just "does it not crash."

### 2. Python `elif` chains and undefined-variable bugs
A single typo (`data` instead of `data_prefix`, or a variable only assigned
in a sibling `elif` branch) breaks **every branch below it in the chain**,
not just the one with the typo — because Python must evaluate each `elif`
condition in sequence to know whether to proceed, and evaluating an undefined
name raises before reaching the correct branch.
- Check every `elif` chain in callback/command dispatchers line by line for
  variable names that don't match what's used elsewhere (`data` vs
  `data_prefix`, `query.data` vs `data`, etc.)
- Test EVERY branch of the dispatcher individually by calling the handler with
  each possible `callback_data`/`payload` value and asserting no exception —
  do not assume "if the first three branches work, the rest do too."

### 3. Reentrant `asyncio.Lock` deadlocks
`asyncio.Lock` is not reentrant. `async with lock: ... async with lock:` (even
nested several calls deep, e.g. inside a helper called from inside the `with`
block) hangs forever — the task waits on a lock it already holds.
- Check every `async with <lock>:` block for any nested acquisition of the
  *same* lock object, including indirectly through a function called from
  within the block.
- Test with `asyncio.wait_for(the_call(), timeout=5)` and assert it doesn't
  raise `TimeoutError` — a hang is invisible in a plain `await` call, so a
  timeout wrapper is mandatory to actually catch it in a test.

### 4. Deep link / callback_data payload consistency
Telegram's `/start` payload has a **hard 64-character limit**. Encoding a
full URL (`?start=analyze_{quote(full_url)}`) blows past this for any
realistic URL with query parameters. Fix: generate a short random token,
store `token -> url` server-side, embed only the token in the link.
- Also check: does every deep link that's supposed to identify *this specific
  user* (referral links) actually use the user's real referral code, not
  their raw numeric Telegram ID? A raw ID formatted to look like a referral
  payload (`ref_{user_id}`) will never match a real `ref_code` and silently
  no-ops. This bug recurred **three separate times** across different files/
  rewrites in this session — grep for `ref_{user_id}` and `ref_{user\.id}` --
  style raw-ID interpolation into anything that also handles `ref_` prefixed
  payloads, every single time code in this area changes.
- Test the full chain: generate the link the way the real code does, extract
  the payload, feed it back into the `/start` handler, assert the expected
  side effect (referral credited, URL resolved, etc.) actually happens.

### 5. PDF generation and non-Latin1 text
Default PDF fonts (Helvetica, Arial, etc. in libraries like fpdf2) only
support Latin-1. If the input data comes from user-typed text and the bot
serves non-Latin-alphabet languages (Cyrillic for Russian/Ukrainian, etc.),
generation crashes on the first non-Latin1 character. Fix: bundle/install a
Unicode-capable TTF font (e.g. `fonts-dejavu-core` via apt, referenced with
`add_font()`), with a graceful fallback if the font file isn't present
(e.g. local Windows dev).
- Test with actual Cyrillic input, not just Latin placeholder text — "Иван
  Иванов" as a name field, not "John Smith."

### 6. Platform-dependent file encoding
`open(path, "w")` without `encoding="utf-8"` uses the OS's default locale
encoding. On Windows with a non-English locale (e.g. Russian, cp1251), this
silently works until a character outside that codepage appears (Cyrillic
handled fine, but "m²", German umlauts, em-dashes, emoji etc. are NOT in
cp1251) — then it crashes with `UnicodeEncodeError: 'charmap' codec...`.
**This cannot be caught by a normal runtime test on Linux CI**, because
Linux's default encoding is already UTF-8 — the bug is invisible in CI and
only manifests on the actual Windows deployment/dev machine. Use a **static
check** instead: parse the source with `ast`, find every `open()` call in
text mode, assert `encoding=` is explicitly passed. See `test_regression.py`'s
`TestFileEncodingIsExplicit` for the reference implementation.

### 7. Honesty/disclosure regressions in auto-posted content
If the bot (or a companion script using a personal Telegram user account)
auto-posts promotional content to groups, any copy that implies "I'm a
satisfied random user" rather than "I'm the developer" is deceptive/
astroturfing, carries real Telegram ToS ban risk for the account doing the
posting, and needs explicit human sign-off to change. Once fixed, **write a
test that asserts the disclosure markers are present** (not just "message
mentions the bot") — this exact regression reverted twice across unrelated
rewrites in this session, and the guard test itself was silently rewritten
to assert the *wrong* (reverted) behavior once. When reviewing a diff to
this kind of file, always diff the test file's assertions too, not just
whether "tests still pass."

## Testing philosophy for this project

- Prefer `unittest.IsolatedAsyncioTestCase` + `unittest.mock.AsyncMock`/`MagicMock`
  to build fake `Update`/`Context` objects and call real handler functions
  directly — this project's existing `test_bot_handlers.py` has good
  `make_update()`-style helpers to reuse/extend.
- Patch storage at the `load_data`/`save_data` level (`@patch("bot.load_data",
  return_value=some_dict)`), not by touching real files — keeps tests fast and
  isolated, and lets you assert on the in-memory dict after the call.
- A test that hardcodes the same string twice and compares them to each other,
  without calling any real project function, is not a test — it's decoration.
  If asked to write "tests that catch bugs," each test must import and call
  actual project code and assert on an observable side effect.
- When fixing a bug found via manual/ad-hoc verification during a chat
  session, always promote that verification into a permanent test before
  moving on — see `test_regression.py`, where every fix in this session got
  a corresponding test, organized by bug with a comment explaining what
  regression it guards against.

## Git workflow constraint

Claude in this environment can `git clone` the repo (read-only, public HTTPS)
but cannot `git push` (no credentials). After committing a fix locally:
```
git format-patch -1 HEAD --stdout > /mnt/user-data/outputs/000N-description.patch
```
then `present_files` it. Tell the user to apply with `git apply <patch>` or
`git am <patch>` (the latter preserves the commit message/author) and then
`git push` themselves. If asked to "check again" after they've pushed,
`git fetch && git reset --hard origin/main` before re-auditing — don't trust
a stale local checkout, and don't assume a previously-applied patch survived
later unrelated commits (regressions from merge/rewrite conflicts happened
more than once in this session).

## Fact-checking an externally-provided audit document

When the user pastes in a bug report/audit (from another tool, another AI, a
freelancer, etc.) and asks for a verdict:
1. Don't take severity labels ("critical"/"serious") at face value — verify
   each one against the actual current code, since the audit may be stale,
   generated from a different commit, or simply wrong about how a library/
   runtime behaves.
2. Actually execute a check for every falsifiable technical claim
   ("X will throw exception Y", "function Z is never called", "config W is
   unused") rather than eyeballing plausibility.
3. Separately flag claims that are inherently not code-verifiable (market/
   competitor research, pricing comparisons) — these can be spot-checked with
   a web search for plausibility but shouldn't be scored the same way as a
   concrete code claim.
4. Give a clear final tally: confirmed / false / needs-more-context, per claim,
   not just an overall vibe. The user needs to know which fixes are worth
   their time.
5. It's normal and expected for a chunk of automated-audit findings to be
   wrong — say so plainly rather than softening it, and explain *why* each
   one was wrong (what was actually tested) so the user can calibrate trust
   in future audits from the same source.
