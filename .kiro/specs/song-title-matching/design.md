# Design Document: Robust Song Title Matching

## Overview

The song-title matching subsystem converts a raw YouTube video title string into a structured `SongSearch(track, artists)` value (`_parse_song_title`) and then decides whether a Spotify API result is a genuine hit for that search (`_is_valid_match`). Eight gaps in the current implementation cause missed matches and false positives. This document describes targeted, surgical fixes to `_parse_song_title`, `_normalize`, `_track_matches`, `_tokens_in_order`, and `_is_valid_match`, plus a full restructure of the test file.

All changes are confined to `youtube2spotify.py` and `test_song_title_matching.py`. No new dependencies are introduced; the Python standard library's `html` module (already available) is used for entity decoding.

---

## Architecture

The subsystem is a pure-function pipeline inside a single Python module:

```
YouTube title (str)
       │
       ▼
 _parse_song_title          ← Fix 1 (html.unescape), Fix 5 (Unicode guard),
       │                         Fix 7 (Topic channel stripping)
       ▼
  SongSearch(track, artists)
       │
       ▼
 SongSearch.queries()       ← unchanged
       │
       ▼
 Spotify API results
       │
       ▼
  _is_valid_match           ← Fix 2/4 (_track_matches short-token guard),
       │                         Fix 3 (multi-artist swap path),
       │                         Fix 6 (_tokens_in_order short-token guard)
       ▼
  bool (accept / reject)
```

All fixes are backward-compatible: existing passing test cases must continue to pass.

---

## Components and Interfaces

### 1. `_parse_song_title(title: str) -> SongSearch | None`

**Change: HTML entity decoding (Req 1)**

Prepend a single call to `html.unescape(title)` as the very first transformation before any regex or segment splitting:

```python
import html as _html

def _parse_song_title(title: str) -> SongSearch | None:
    if not title or title.strip().lower() in {"private video", "deleted video"}:
        return None
    title = _html.unescape(title)   # NEW — decode &amp; etc.
    ...
```

This ensures `"Skrillex &amp; Damian Marley - Make It Bun Dem"` becomes `"Skrillex & Damian Marley - Make It Bun Dem"` before `_ARTIST_SPLIT` splits on `&`.

**Change: Unicode / accented title preservation (Req 5)**

After `_normalize` is called for segment comparison, guard against the normalised result being empty. Where the parser currently passes normalised strings to segment checks, retain the original pre-normalisation value for the `SongSearch` fields:

- `_extract_artists` and `_parse_track_segment` already receive the un-normalised segment — keep that.
- In `_is_junk_segment`, the early `len(segment) > 80` guard handles over-long strings.
- Non-ASCII segments (e.g. `"ΑΜΜΟΧΩΣΤΟΣ - ΧΩΜΑ ΠΟΥ ΠΕΡΠΑΤΗΣΑ"`) survive `_SEGMENT_SPLIT` because the dash ` - ` is ASCII; after splitting, each segment consists of Greek characters. `_JUNK_SEGMENT` and `_JUNK_CONTAINS` patterns are ASCII-only and will not match, so the segments survive. No additional code change is needed beyond the existing logic — but a regression test is required (Req 8.4).

**Change: YouTube Topic channel stripping (Req 7)**

Add `"topic"` to `_JUNK_SEGMENT` regex so it is already handled by `_is_junk_segment`. The pattern already contains `"topic"` in the existing `_JUNK_SEGMENT` regex (`topic` is listed). Verify that the *segment* `"Topic"` is correctly stripped. For titles like `"Bohemian Rhapsody - Queen - Topic"`, the three-segment path in `_parse_song_title` already pops the first segment when it does not look like an artist. The `"Topic"` segment is the *last* segment; `_is_junk_segment` will filter it out when segments are cleaned.

However, the current code only filters junk *before* genre stripping at the front; trailing junk segments are not removed. A small extension is needed:

```python
# After the existing leading-genre / leading-non-artist trim:
segments = [s for s in segments if not _is_junk_segment(s)]
# (move this filter to after the initial segment split, before the length checks)
```

Re-ordering the filter so it runs after `_clean_segment` and before length decisions ensures `"Topic"` is removed from any position.

### 2. `_track_matches(expected: str, spotify_name: str) -> bool`

**Change: Short-token exact-match guard (Req 2 & 4)**

```python
def _track_matches(expected: str, spotify_name: str) -> bool:
    exp_norm = _normalize(expected)
    got_norm = _normalize(spotify_name)

    if exp_norm == got_norm:
        return True

    exp_tokens = exp_norm.split()
    got_tokens = got_norm.split()
    if not exp_tokens:
        return False

    if _tokens_in_order(exp_tokens, got_tokens):
        return True

    if len(exp_tokens) == 1:
        token = exp_tokens[0]
        # NEW: short tokens require an exact full-string match
        if len(token) < 4:
            return exp_norm == got_norm   # already handled above, always False here
        return token in got_tokens        # 4+ char token: membership test

    return False
```

The guard `len(token) < 4` means single-token expected names shorter than 4 characters (e.g. `"one"`, `"fly"`) will only match if the Spotify track name normalises to exactly that word, preventing "One" from matching "One More Time".

### 3. `_tokens_in_order(needles, haystack) -> bool`

**Change: Short-needle strictness (Req 6)**

```python
def _tokens_in_order(needles: list[str], haystack: list[str]) -> bool:
    haystack_set = set(haystack)
    idx = 0
    for token in haystack:
        if idx < len(needles) and token == needles[idx]:
            # NEW: short needles must be an exact token match (already guaranteed
            # by token == needles[idx]), but we also skip advancement if the needle
            # is very short and appears as a sub-token match elsewhere.
            idx += 1
    return idx == len(needles)
```

The current implementation already does exact token comparison (`token == needles[idx]`). The real problem is that a short expected track name (1–3 chars) is sent through `_tokens_in_order` from `_track_matches` — the fix in `_track_matches` intercepts that before reaching this function. Additionally, add a minimum needle length guard: if any needle is fewer than 2 characters, skip it in the subsequence check (avoid matching single-letter words like "a", "i"):

```python
_MIN_NEEDLE_LEN = 2   # module-level constant

def _tokens_in_order(needles: list[str], haystack: list[str]) -> bool:
    meaningful = [n for n in needles if len(n) >= _MIN_NEEDLE_LEN]
    if not meaningful:
        return False
    idx = 0
    for token in haystack:
        if idx < len(meaningful) and token == meaningful[idx]:
            idx += 1
    return idx == len(meaningful)
```

### 4. `_is_valid_match(search: SongSearch, spotify_track: dict) -> bool`

**Change: Multi-artist swap path (Req 3)**

```python
def _is_valid_match(search: SongSearch, spotify_track: dict) -> bool:
    spotify_name = spotify_track["name"]
    spotify_artists = [a["name"] for a in spotify_track["artists"]]

    if _track_matches(search.track, spotify_name):
        if search.artists and not _artists_match(search.artists, spotify_artists):
            return False
        return True

    if not search.artists:
        return False

    # NEW: try every artist as a candidate swapped track name
    for candidate_track in search.artists:
        if _track_matches(candidate_track, spotify_name):
            if _artists_match([search.track], spotify_artists):
                return True

    return False
```

Iterating over all `search.artists` instead of only `search.artists[0]` handles reversed multi-artist titles like `"Numb/Encore - Linkin Park / Jay-Z"` where `search.artists = ["Linkin Park", "Jay-Z"]` and the Spotify track name is `"Numb/Encore"`.

---

## Data Models

No new data models are introduced. `SongSearch` remains unchanged:

```python
@dataclass(frozen=True)
class SongSearch:
    track: str
    artists: list[str]
```

The `_normalize` function remains unchanged. All fixes operate on string comparisons and control flow.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: HTML Entity Round-Trip Transparency

*For any* YouTube video title string, parsing the `html.unescape`-decoded version of the title SHALL produce a `SongSearch` that is equal to parsing the title with all HTML entities manually pre-expanded. In other words, `_parse_song_title(html.unescape(t))` is equivalent to `_parse_song_title` applied after manual entity substitution.

**Validates: Requirements 1.1, 1.2, 1.3**

---

### Property 2: Short-Track Non-Containment

*For any* `SongSearch` whose `track` field normalises to a single token of fewer than 4 characters, and *for any* Spotify track whose normalised name contains that short token as a proper sub-sequence (but is not exactly equal to it), `_is_valid_match` SHALL return `False`.

**Validates: Requirements 2.1, 4.1**

---

### Property 3: Swap-Path Completeness

*For any* `SongSearch(track=T, artists=[A1, A2, ...])` and Spotify result where the Spotify track name normalises to match one of the `Ai`, `_is_valid_match` SHALL return `True` if and only if `T` also normalises to match one of the Spotify artist names.

**Validates: Requirements 3.1, 3.2, 3.3**

---

### Property 4: Normalised Artist Preservation

*For any* title containing accented or non-ASCII characters that is not in the discard list and has at least one valid segment after junk filtering, `_parse_song_title` SHALL return a non-`None` `SongSearch` whose `track` and `artists` fields are non-empty strings.

**Validates: Requirements 5.1, 5.3**

---

### Property 5: Topic Channel Segment Removal

*For any* title of the form `"<A> - <B> - Topic"` (where A and B are non-junk, non-genre strings), `_parse_song_title` SHALL return the same `SongSearch` as it would for `"<A> - <B>"`.

**Validates: Requirements 7.1, 7.2**

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `title` is `None` or empty string | Return `None` (existing guard, unchanged) |
| `title` is `"private video"` / `"deleted video"` | Return `None` (existing guard, unchanged) |
| All segments are junk after filtering | Return `None` (existing behaviour preserved) |
| `html.unescape` raises (malformed entity) | Python's `html.unescape` never raises on well-formed input; malformed entities are passed through unchanged — no additional guard needed |
| `_normalize` produces an empty string for a non-ASCII token | Retain the original un-normalised segment string; do not return `None` solely due to normalisation loss |

---

## Testing Strategy

### Framework

Python's built-in `unittest` module — already in use; no new test dependency.

For property-based tests, use **Hypothesis** (`pip install hypothesis`), which is the standard PBT library for Python. Each property test is configured to run a minimum of 100 examples (`@settings(max_examples=100)`).

### Test File Restructure (Req 8)

The single test file `test_song_title_matching.py` is restructured into four focused test classes:

| Class | Scope |
|---|---|
| `TestParseSongTitleHappyPath` | Well-formed `artist – track` titles, asserts both `track` and `artists` |
| `TestParseSongTitleEdgeCases` | Non-songs, HTML entities, accented chars, Topic channel, remix-only, Greek titles |
| `TestIsValidMatchTruePositives` | Cases where `_is_valid_match` should return `True` |
| `TestIsValidMatchFalsePositives` | Cases where `_is_valid_match` should return `False` (short tracks, wrong artist, etc.) |

### Unit Tests

- Every entry in `PARSE_SONG_TITLE_CASES` asserts both `parsed.track` and `parsed.artists`.
- `TestParseSongTitleEdgeCases` includes subtests for `&amp;`, Greek titles, accented artists, Topic channel format, remix-only titles.
- `TestIsValidMatchFalsePositives` includes a subtest for `SongSearch(track="One", artists=["Metallica"])` against a Spotify track whose name contains "one" but is not equal to it.
- Real-playlist fixture test asserts specific `track` values for at least 5 known-good titles (e.g. "David Guetta - Titanium ft. Sia" → track `"Titanium"`).

### Property-Based Tests

Property tests use `hypothesis.strategies` to generate inputs. Each test is tagged with a comment referencing its design property.

**Property 1 — `test_html_entity_round_trip`**

Strategy: generate strings from a small alphabet, randomly insert `&amp;` entities, assert that parsing the unescape-decoded title equals parsing a manually substituted version.
Tag: `# Feature: song-title-matching, Property 1: HTML entity round-trip transparency`

**Property 2 — `test_short_track_no_false_positive`**

Strategy: generate single-token expected track names of 1–3 characters; generate Spotify track names that contain the token but are longer. Assert `_is_valid_match` returns `False`.
Tag: `# Feature: song-title-matching, Property 2: short-track non-containment`

**Property 3 — `test_swap_path_completeness`**

Strategy: generate a list of one or more artist name strings and a track name. Construct a `SongSearch`. Build a Spotify result where the track name equals one `Ai` and one artist equals `T`. Assert `_is_valid_match` returns `True`.
Tag: `# Feature: song-title-matching, Property 3: swap-path completeness`

**Property 4 — `test_accented_title_non_null`**

Strategy: generate titles composed of characters from `unicodedata` categories `Ll`/`Lu` (Latin extended, Greek, accented), with a ` - ` separator. Assert `_parse_song_title` returns non-`None`.
Tag: `# Feature: song-title-matching, Property 4: normalised artist preservation`

**Property 5 — `test_topic_channel_same_as_without_topic`**

Strategy: generate two non-junk, non-genre strings A and B. Assert `_parse_song_title(f"{A} - {B} - Topic") == _parse_song_title(f"{A} - {B}")`.
Tag: `# Feature: song-title-matching, Property 5: topic channel segment removal`
