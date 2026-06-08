# Implementation Plan: Robust Song Title Matching

## Overview

Fix eight known correctness gaps in `youtube2spotify.py` and restructure `test_song_title_matching.py`. Each task is a discrete, incremental code change. Tasks build on one another; integration is completed in the final wiring task.

---

## Tasks

- [ ] 1. Add HTML entity decoding to `_parse_song_title`
  - Import `html` from the Python standard library at the top of `youtube2spotify.py`
  - Add `title = html.unescape(title)` as the first transformation inside `_parse_song_title`, immediately after the early-return guard for empty / deleted / private titles
  - This ensures `&amp;`, `&quot;`, `&#39;` and other entities are resolved before any regex or segment splitting runs
  - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 1.1 Write property test for HTML entity round-trip
    - **Property 1: HTML Entity Round-Trip Transparency**
    - Use `hypothesis.strategies.text` with an alphabet that includes `&amp;` injections; assert `_parse_song_title` result equals parsing the manually pre-decoded string
    - **Validates: Requirements 1.1, 1.2, 1.3**

- [ ] 2. Harden `_track_matches` with short-token exact-match guard
  - In the `len(exp_tokens) == 1` branch of `_track_matches`, replace the current unconditional `token in got_tokens` test with: if `len(token) < 4` return `exp_norm == got_norm`; otherwise return `token in got_tokens`
  - The `exp_norm == got_norm` path is already handled by the early equality check, so the `< 4` branch will always be `False` for the token-presence code path — preventing short tokens from matching via substring
  - _Requirements: 2.1, 2.2, 4.1, 4.2_

  - [ ]* 2.1 Write property test for short-track non-containment
    - **Property 2: Short-Track Non-Containment**
    - Generate single tokens of length 1–3; generate Spotify names that contain but don't equal them; assert `_is_valid_match` returns `False`
    - **Validates: Requirements 2.1, 4.1**

- [ ] 3. Fix multi-artist swap path in `_is_valid_match`
  - Replace the single `swapped_track = search.artists[0]` + `_track_matches(swapped_track, ...)` block with a `for candidate_track in search.artists:` loop
  - Inside the loop: if `_track_matches(candidate_track, spotify_name)` AND `_artists_match([search.track], spotify_artists)`, return `True`
  - After the loop, return `False`
  - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 3.1 Write property test for swap-path completeness
    - **Property 3: Swap-Path Completeness**
    - Generate a list of ≥1 artist strings and a track string; build a Spotify result where `name` = one of the artists and `artists` = `[track]`; assert `_is_valid_match` returns `True`. Also generate the rejection case (Spotify track artist ≠ `search.track`) and assert `False`.
    - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ] 4. Add minimum-length needle guard to `_tokens_in_order`
  - Add a module-level constant `_MIN_NEEDLE_LEN = 2`
  - At the start of `_tokens_in_order`, filter `needles` to `[n for n in needles if len(n) >= _MIN_NEEDLE_LEN]`; if the filtered list is empty, return `False`
  - This prevents single-character noise tokens ("a", "i") from satisfying a subsequence match
  - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 4.1 Write unit tests for `_tokens_in_order` short-needle behaviour
    - Assert that `_tokens_in_order(["a"], ["a", "song"])` returns `False` (single-char needle filtered out)
    - Assert that `_tokens_in_order(["song"], ["song"])` still returns `True`
    - _Requirements: 6.1, 6.3_

- [ ] 5. Verify Unicode / accented title preservation (defensive guard)
  - In `_parse_song_title`, after the call to `_clean_segment` / `_extract_artists`, confirm that segments derived from non-ASCII text are not inadvertently discarded by `_is_junk_segment`
  - If `_normalize(segment)` returns an empty string but the original `segment` is non-empty, the segment should be retained as-is rather than treated as junk — add this guard inside `_is_junk_segment`: `if not segment or len(segment) > 80` already handles empty, but do not return `True` for segments whose normalised form is empty while the raw form is non-empty
  - Specifically: change the first condition in `_is_junk_segment` from `if not segment` to `if not segment.strip()`; no other change needed if `_JUNK_SEGMENT` and `_JUNK_CONTAINS` patterns are ASCII-only (they are)
  - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 5.1 Write property test for accented/non-ASCII title non-null result
    - **Property 4: Normalised Artist Preservation**
    - Generate titles of form `"X - Y"` where X and Y are strings from `hypothesis.strategies.text(alphabet=hypothesis.strategies.characters(whitelist_categories=("Ll","Lu","Nd")))` filtered to non-empty, non-junk strings; assert `_parse_song_title` returns non-`None`
    - **Validates: Requirements 5.1, 5.3**

- [ ] 6. Add YouTube Topic channel segment stripping
  - Confirm `"topic"` is in the `_JUNK_SEGMENT` regex (it already appears in the pattern); if missing, add it
  - Move the `segments = [s for s in segments if s and not _is_junk_segment(s)]` filter to run **after** `_clean_segment` is applied to all segments and **before** the length-based decisions — this ensures `"Topic"` at any position (not just the leading junk-strip) is removed
  - Currently the filter runs once; make sure it runs before the `if not segments` guard and before the `if len(segments) >= 3` path
  - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 6.1 Write property test for Topic channel equivalence
    - **Property 5: Topic Channel Segment Removal**
    - Generate pairs of non-junk, non-genre strings (A, B); assert `_parse_song_title(f"{A} - {B} - Topic") == _parse_song_title(f"{A} - {B}")`
    - **Validates: Requirements 7.1, 7.2**

- [ ] 7. Checkpoint — ensure all unit tests pass
  - Run `python -m pytest test_song_title_matching.py -v` (or `python -m unittest discover`)
  - All existing tests must pass before proceeding to test restructuring
  - Ensure all tests pass; ask the user if questions arise.

- [ ] 8. Restructure `test_song_title_matching.py`
  - Split the file into four focused test classes:
    - `TestParseSongTitleHappyPath` — the existing `PARSE_SONG_TITLE_CASES` list; each `subTest` asserts `parsed.track` AND `parsed.artists` individually
    - `TestParseSongTitleEdgeCases` — non-song entries, `&amp;` titles, Greek / accented titles, Topic channel format, remix-only titles, bare-track single-segment titles
    - `TestIsValidMatchTruePositives` — all cases where `_is_valid_match` should return `True`
    - `TestIsValidMatchFalsePositives` — all cases where `_is_valid_match` should return `False`
  - _Requirements: 8.1, 8.2_

  - [ ]* 8.1 Add `&amp;` decode test
    - Assert `_parse_song_title("Skrillex &amp; Damian Marley - Make It Bun Dem")` returns `SongSearch(track="Make It Bun Dem", artists=["Skrillex", "Damian Marley"])`
    - _Requirements: 8.3_

  - [ ]* 8.2 Add accented artist test
    - Assert `_parse_song_title("Rosalía - DESPECHÁ")` returns `SongSearch(track="DESPECHÁ", artists=["Rosalía"])`
    - _Requirements: 8.4_

  - [ ]* 8.3 Add short-track false-positive rejection test
    - Assert `_is_valid_match(SongSearch(track="One", artists=["Metallica"]), {"name": "One More Time", "artists": [{"name": "Daft Punk"}]})` returns `False`
    - _Requirements: 8.5_

  - [ ]* 8.4 Add remix/noise-only title test
    - Assert `_parse_song_title("(Official Remix)")` returns `None` or a `SongSearch` with a non-empty `track` field (whichever the implementation produces — document the expected behaviour)
    - _Requirements: 8.6_

  - [ ]* 8.5 Add Topic channel format test
    - Assert `_parse_song_title("Bohemian Rhapsody - Queen - Topic")` returns `SongSearch(track="Bohemian Rhapsody", artists=["Queen"])`
    - _Requirements: 8.7_

  - [ ]* 8.6 Add real-playlist content assertions
    - For at least 5 titles from the existing `raw_titles` fixture, add explicit `assertEqual` assertions for the expected `track` value:
      - `"David Guetta - Titanium ft. Sia (Official Video)"` → track `"Titanium"`
      - `"Gotye - Somebody That I Used To Know (feat. Kimbra) [Official Music Video]"` → track `"Somebody That I Used To Know"`
      - `"Skrillex &amp; Damian \"Jr. Gong\" Marley - Make It Bun Dem [OFFICIAL VIDEO]"` → track `"Make It Bun Dem"`
      - `"Adventure Club &amp; Krewella - Rise &amp; Fall"` → track `"Rise & Fall"`
      - `"Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video)"` → track `"Don't You Worry Child"`
    - _Requirements: 8.8_

- [ ] 9. Final checkpoint — ensure all tests pass
  - Run the full test suite including any newly written property tests
  - Ensure all tests pass; ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional sub-tasks and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Tasks 1–6 are independent production-code fixes and can be implemented in any order
- Task 7 is the integration checkpoint before test restructuring begins
- Property tests require `hypothesis` to be installed (`pip install hypothesis`)
- The `_MIN_NEEDLE_LEN` constant introduced in Task 4 is a module-level change; verify it does not break existing `_tokens_in_order` call sites

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2", "3", "4", "5", "6"] },
    { "wave": 2, "tasks": ["7"] },
    { "wave": 3, "tasks": ["8"] },
    { "wave": 4, "tasks": ["9"] }
  ]
}
```
