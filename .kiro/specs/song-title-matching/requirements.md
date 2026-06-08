# Requirements Document

## Introduction

The YouTube-to-Spotify playlist converter must reliably parse YouTube video titles into structured artist/track data (`_parse_song_title`) and then validate that a Spotify search result is a genuine match for that data (`_is_valid_match`). The current implementation contains a set of known correctness gaps that cause missed matches and false positives. This spec covers hardening both functions and restructuring the test suite to prevent regressions.

## Glossary

- **Parser**: The `_parse_song_title` function that converts a raw YouTube video title string into a `SongSearch` value.
- **Matcher**: The `_is_valid_match` function that decides whether a Spotify track result is a genuine match for a `SongSearch` value.
- **SongSearch**: The frozen dataclass `SongSearch(track: str, artists: list[str])` produced by the Parser.
- **HTML_Entity**: A percent-encoded or named HTML entity such as `&amp;` that may appear in YouTube API title strings.
- **Token**: A single whitespace-delimited word produced after Unicode normalisation and punctuation removal.
- **Short_Token**: A normalised token whose length is strictly less than 4 characters.
- **Swap_Path**: The `_is_valid_match` code path that tests whether the YouTube title was written in reversed order (`track – artist` instead of `artist – track`).
- **Topic_Channel**: A YouTube auto-generated channel that publishes videos with titles in the format `<Song Title> - Topic`.
- **Normaliser**: The `_normalize` helper that lower-cases a string and replaces all non-word characters with spaces.

---

## Requirements

### Requirement 1: HTML Entity Decoding

**User Story:** As a user with YouTube playlists that contain `&amp;` (and other HTML entities) in video titles, I want those entities decoded before parsing, so that artists and tracks are extracted correctly rather than appearing as raw entity strings.

#### Acceptance Criteria

1. WHEN the Parser receives a title containing the `&amp;` HTML entity, THE Parser SHALL decode `&amp;` to `&` before performing any segment splitting or artist extraction.
2. WHEN the Parser receives a title containing any other standard HTML entity (e.g. `&quot;`, `&apos;`, `&#39;`, `&lt;`, `&gt;`), THE Parser SHALL decode those entities to their Unicode equivalents before parsing.
3. WHEN the Parser receives a title that contains no HTML entities, THE Parser SHALL produce the same output as it would without an entity-decoding step.

---

### Requirement 2: False-Positive Prevention for Short Track Names

**User Story:** As a developer, I want the Matcher to avoid accepting Spotify tracks whose titles merely contain a short common word that happens to equal the expected track name, so that songs like "One" by Metallica do not match unrelated songs that contain the word "one".

#### Acceptance Criteria

1. WHEN the Matcher evaluates `_track_matches` and the normalised expected track name is a single token of fewer than 4 characters, THE Matcher SHALL require an exact full-string match against the normalised Spotify track name.
2. WHEN the Matcher evaluates `_track_matches` and the normalised expected track name is a single token of 4 or more characters, THE Matcher SHALL accept a match when that token appears anywhere in the normalised Spotify track name token list.
3. WHEN the Matcher evaluates `_track_matches` and the normalised expected track name contains two or more tokens, THE Matcher SHALL use the existing ordered-token subsequence logic unchanged.

---

### Requirement 3: Multi-Artist Swap Matching

**User Story:** As a user whose YouTube playlist contains reversed-format titles such as "Take On Me - a-ha" or "Numb/Encore - Linkin Park / Jay-Z", I want the Matcher to try every parsed artist as a candidate swapped track name, so that reversed multi-artist titles are resolved correctly.

#### Acceptance Criteria

1. WHEN the Matcher reaches the Swap_Path and `search.artists` contains one or more entries, THE Matcher SHALL attempt `_track_matches` for every entry in `search.artists`, not only `search.artists[0]`.
2. WHEN any artist entry in `search.artists` matches the Spotify track name via `_track_matches`, THE Matcher SHALL verify that `search.track` matches one of the Spotify artist names, and IF that verification fails THE Matcher SHALL reject the candidate track.
3. WHEN no entry in `search.artists` matches the Spotify track name, THE Matcher SHALL reject the candidate track.

---

### Requirement 4: Minimum Length Guard on Token-Based Track Matching

**User Story:** As a developer, I want `_track_matches` to require that single-token expected track names meet a minimum character length before being accepted via substring/token presence, so that noise words do not cause false positives.

#### Acceptance Criteria

1. WHEN `_track_matches` is called with a normalised expected track name that is a single token of fewer than 4 characters, THE Matcher SHALL only accept a result if the normalised Spotify track name is exactly equal to that token.
2. WHEN `_track_matches` is called with a normalised expected track name that is a single token of 4 or more characters, THE Matcher SHALL accept a result only when that token is present as a member of the normalised Spotify track name's token list.

*Note: Requirements 2 and 4 both refine the same function; they are stated separately to make the two distinct rules (exact-match for short tokens, token-presence for longer tokens) independently verifiable.*

---

### Requirement 5: Unicode and Accented Title Preservation

**User Story:** As a user with playlists containing non-Latin or accented titles (e.g. Greek, Spanish, French), I want the Parser to preserve those titles rather than discarding them silently, so that accented and non-ASCII songs are not lost.

#### Acceptance Criteria

1. WHEN the Parser receives a title whose text consists entirely of non-ASCII Unicode characters (e.g. a Greek title), THE Parser SHALL return a non-`None` `SongSearch` value if the title is not in the known discard list (`"private video"`, `"deleted video"`), provided no other parsing logic (such as empty-segment detection) requires returning `None`.
2. WHEN the Normaliser is applied to a string of non-ASCII characters and the result would be empty after stripping, THE Parser SHALL retain the original (un-normalised) string for matching purposes rather than discarding the title.
3. WHEN the Parser receives a title containing accented Latin characters (e.g. "Rosalía", "DÁKITI"), THE Parser SHALL include those characters in the produced `SongSearch` track and artist fields without stripping them.

---

### Requirement 6: `_tokens_in_order` Short-Token Guard

**User Story:** As a developer, I want the `_tokens_in_order` subsequence check to be stricter for very short tokens, so that single-character or two-character tokens do not inadvertently satisfy a match against unrelated tracks.

#### Acceptance Criteria

1. WHEN `_tokens_in_order` is called and any needle token has fewer than 4 characters, THE system SHALL require an exact positional match for that token (i.e. the token must appear in the haystack, not just be a substring of a haystack token).
2. WHEN all needle tokens are 4 or more characters, THE system SHALL apply the existing sequential-scan matching logic unchanged.
3. WHEN `_tokens_in_order` is used inside `_track_matches` for a multi-token expected name, THE Matcher SHALL inherit the stricter behaviour for short tokens introduced by this requirement.

---

### Requirement 7: YouTube Topic Channel Format Parsing

**User Story:** As a user whose YouTube playlist contains auto-generated Topic channel videos (e.g. "Bohemian Rhapsody - Queen - Topic"), I want the Parser to correctly extract the track name and artist, so that those songs are matched on Spotify.

#### Acceptance Criteria

1. WHEN the Parser encounters a title that ends with the segment `"Topic"` (case-insensitive) after splitting on ` – ` or ` - `, THE Parser SHALL discard that trailing `"Topic"` segment before further processing.
2. WHEN a title in the form `"<Track> - <Artist> - Topic"` is parsed after discarding the `"Topic"` segment, THE Parser SHALL handle the remaining two segments using the existing swap-detection logic so that both orderings (`artist – track` and `track – artist`) produce a correct `SongSearch`.
3. WHEN the title ends with `"Topic"` but has only one non-junk segment remaining after discarding it, THE Parser SHALL treat that segment as a bare track name with no artists.

---

### Requirement 8: Test File Restructuring

**User Story:** As a developer, I want the test suite to be organised into focused, well-named test classes and methods, so that failures are easy to locate and new edge cases are easy to add.

#### Acceptance Criteria

1. THE Test_Suite SHALL contain separate test classes for (a) `_parse_song_title` happy-path cases, (b) `_parse_song_title` edge cases, (c) `_is_valid_match` true-positive cases, and (d) `_is_valid_match` false-positive / rejection cases.
2. WHEN a `_parse_song_title` happy-path test case exists or is added, THE Test_Suite SHALL assert both the extracted `track` field and the extracted `artists` list individually for every such case, not only that the result is non-`None`.
3. THE Test_Suite SHALL include at least one test that asserts the correct `SongSearch` output for a title containing `&amp;`.
4. THE Test_Suite SHALL include at least one test that asserts the correct `SongSearch` output for a title with an accented artist name (e.g. "Rosalía - DESPECHÁ").
5. THE Test_Suite SHALL include at least one test that verifies `_is_valid_match` returns `False` when a single short-token track name (e.g. "One") is tested against a Spotify track that merely contains that word in a longer title.
6. THE Test_Suite SHALL include at least one test that verifies `_is_valid_match` returns `False` for a remix-only or noise-only title (e.g. a title from which `_parse_song_title` cannot derive a meaningful track name).
7. THE Test_Suite SHALL include at least one test covering the YouTube Topic channel format (e.g. `"Bohemian Rhapsody - Queen - Topic"`).
8. WHEN the real-playlist title fixture is used in tests, THE Test_Suite SHALL assert the specific `track` value produced for at least 5 representative titles, not only that the result is non-`None`.
