import unittest

from youtube2spotify import (
    SongSearch,
    _is_valid_match,
    _parse_song_title,
    _tokens_in_order,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

PARSE_SONG_TITLE_CASES = [
    ("Chuck Berry - Johnny B. Goode", "Johnny B. Goode", ["Chuck Berry"]),
    ("The Beatles - Let It Be (Remastered 2009)", "Let It Be", ["The Beatles"]),
    ("Queen - Bohemian Rhapsody (Official Video)", "Bohemian Rhapsody", ["Queen"]),
    ("Nirvana - Smells Like Teen Spirit [HD]", "Smells Like Teen Spirit", ["Nirvana"]),
    ("AC/DC - Back In Black", "Back In Black", ["AC", "DC"]),
    ("Metallica - One (Official Music Video)", "One", ["Metallica"]),
    ("Tupac - California Love ft. Dr. Dre", "California Love", ["Tupac", "Dr. Dre"]),
    ("Eminem ft. Rihanna - Love The Way You Lie", "Love The Way You Lie", ["Eminem", "Rihanna"]),
    ("Drake - One Dance", "One Dance", ["Drake"]),
    ("Kendrick Lamar - HUMBLE. (Music Video)", "HUMBLE.", ["Kendrick Lamar"]),
    ("Michael Jackson - Billie Jean", "Billie Jean", ["Michael Jackson"]),
    ("Whitney Houston - I Will Always Love You", "I Will Always Love You", ["Whitney Houston"]),
    ("Sade - Smooth Operator (Live)", "Smooth Operator", ["Sade"]),
    ("Miles Davis - So What", "So What", ["Miles Davis"]),
    ("Mozart - Requiem: Lacrimosa", "Requiem: Lacrimosa", ["Mozart"]),
    ("Vivaldi - Four Seasons: Winter", "Four Seasons: Winter", ["Vivaldi"]),
    ("Calvin Harris - Summer", "Summer", ["Calvin Harris"]),
    ("The Weeknd - Blinding Lights (Official Audio)", "Blinding Lights", ["The Weeknd"]),
    ("Avicii - Wake Me Up", "Wake Me Up", ["Avicii"]),
    ("Armin van Buuren - Blah Blah Blah (Extended Mix)", "Blah Blah Blah", ["Armin van Buuren"]),
    ("Bad Bunny x Jhayco - DÁKITI", "DÁKITI", ["Bad Bunny x Jhayco"]),
    ("Rosalía - DESPECHÁ", "DESPECHÁ", ["Rosalía"]),
    ("BTS - Dynamite (Official MV)", "Dynamite", ["BTS"]),
    ("Adele - Hello (Official Video)", "Hello", ["Adele"]),
    ("Shania Twain - Man! I Feel Like A Woman!", "Man! I Feel Like A Woman!", ["Shania Twain"]),
    ("Country - Johnny Cash - Ring of Fire", "Ring of Fire", ["Johnny Cash"]),
    ("Hip Hop - Dr. Dre - Still D.R.E. ft. Snoop Dogg", "Still D.R.E.", ["Dr. Dre", "Snoop Dogg"]),
    ("Lofi - Jinsang - affection", "affection", ["Jinsang"]),
    ("Lady Gaga & Ariana Grande - Rain On Me", "Rain On Me", ["Lady Gaga", "Ariana Grande"]),
    ("Linkin Park / Jay-Z - Numb/Encore", "Numb/Encore", ["Linkin Park", "Jay-Z"]),
]


# ---------------------------------------------------------------------------
# 1. TestTokensInOrder
# ---------------------------------------------------------------------------

class TestTokensInOrder(unittest.TestCase):
    """Tests for _tokens_in_order minimum-length needle guard (Req 6.1, 6.3)."""

    def test_single_char_needle_returns_false(self):
        """A single-character needle is filtered out; empty meaningful list → False."""
        self.assertFalse(_tokens_in_order(["a"], ["a", "song"]))

    def test_single_char_needle_exact_haystack_still_false(self):
        """Even when haystack equals the needle, a 1-char needle is filtered → False."""
        self.assertFalse(_tokens_in_order(["i"], ["i"]))

    def test_all_short_needles_returns_false(self):
        """All needles below the minimum length → meaningful is empty → False."""
        self.assertFalse(_tokens_in_order(["a", "i"], ["a", "i", "song"]))

    def test_normal_needle_still_matches(self):
        """A needle of 4+ chars follows the existing sequential-scan logic."""
        self.assertTrue(_tokens_in_order(["song"], ["song"]))

    def test_mixed_needles_short_ones_ignored(self):
        """Short needles are stripped; only the long needle must be matched."""
        self.assertTrue(_tokens_in_order(["a", "song"], ["song"]))

    def test_two_char_needle_passes_through(self):
        """A 2-char needle meets _MIN_NEEDLE_LEN=2 and is NOT filtered out."""
        self.assertTrue(_tokens_in_order(["it"], ["it", "rocks"]))

    def test_two_meaningful_needles_in_order(self):
        """Two needles of sufficient length must appear in order in the haystack."""
        self.assertTrue(_tokens_in_order(["take", "me"], ["take", "on", "me"]))

    def test_two_meaningful_needles_out_of_order(self):
        """Needles present but in wrong order → False."""
        self.assertFalse(_tokens_in_order(["me", "take"], ["take", "on", "me"]))


# ---------------------------------------------------------------------------
# 2. TestParseSongTitleHappyPath
# ---------------------------------------------------------------------------

class TestParseSongTitleHappyPath(unittest.TestCase):
    """Well-formed 'artist – track' titles; asserts both track and artists (Req 8.1, 8.2)."""

    def test_parse_song_title_across_genres_and_eras(self):
        for title, expected_track, expected_artists in PARSE_SONG_TITLE_CASES:
            with self.subTest(title=title):
                parsed = _parse_song_title(title)
                self.assertIsNotNone(parsed, msg=f"Expected non-None for {title!r}")
                self.assertEqual(expected_track, parsed.track)
                self.assertEqual(expected_artists, parsed.artists)


# ---------------------------------------------------------------------------
# 3. TestParseSongTitleEdgeCases
# ---------------------------------------------------------------------------

class TestParseSongTitleEdgeCases(unittest.TestCase):
    """Edge cases for _parse_song_title: non-songs, HTML entities, accents, Topic, etc."""

    # --- non-song entries (Req 8.1) ---

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_song_title(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(_parse_song_title("   "))

    def test_private_video_lower_returns_none(self):
        self.assertIsNone(_parse_song_title("Private video"))

    def test_private_video_upper_returns_none(self):
        self.assertIsNone(_parse_song_title("private video"))

    def test_deleted_video_lower_returns_none(self):
        self.assertIsNone(_parse_song_title("Deleted video"))

    def test_deleted_video_upper_returns_none(self):
        self.assertIsNone(_parse_song_title("DELETED VIDEO"))

    # --- HTML entity decoding (Req 8.3) ---

    def test_amp_entity_decoded_before_split(self):
        """&amp; is decoded to & so the artist split works correctly (Req 8.3)."""
        result = _parse_song_title("Skrillex &amp; Damian Marley - Make It Bun Dem")
        self.assertIsNotNone(result)
        self.assertEqual("Make It Bun Dem", result.track)
        self.assertEqual(["Skrillex", "Damian Marley"], result.artists)

    # --- Accented / non-ASCII titles (Req 8.4) ---

    def test_accented_artist_preserved(self):
        """Accented characters in artist name are kept intact (Req 8.4)."""
        result = _parse_song_title("Rosalía - DESPECHÁ")
        self.assertIsNotNone(result)
        self.assertEqual("DESPECHÁ", result.track)
        self.assertEqual(["Rosalía"], result.artists)

    # --- YouTube Topic channel stripping (Req 7, 8.7) ---

    def test_topic_segment_is_stripped(self):
        """'Topic' is recognised as junk and removed before length-based decisions."""
        result = _parse_song_title("Bohemian Rhapsody - Queen - Topic")
        self.assertIsNotNone(result)
        self.assertEqual(result.track, "Queen")
        self.assertEqual(result.artists, ["Bohemian Rhapsody"])

    def test_topic_case_insensitive(self):
        """'topic' and 'TOPIC' are both treated as junk."""
        lower = _parse_song_title("Take On Me - a-ha - topic")
        upper = _parse_song_title("Take On Me - a-ha - TOPIC")
        no_topic = _parse_song_title("Take On Me - a-ha")
        self.assertEqual(lower, upper)
        self.assertEqual(lower, no_topic)

    def test_single_segment_after_topic_stripped_is_bare_track(self):
        """When only one non-junk segment remains after Topic removal, treat as bare track."""
        result = _parse_song_title("Imagine - Topic")
        self.assertIsNotNone(result)
        self.assertEqual(result.track, "Imagine")
        self.assertEqual(result.artists, [])

    # --- Remix / noise-only title (Req 8.6) ---

    def test_noise_only_title_returns_none(self):
        """A title whose only content is parenthesised junk leaves no segments → None (Req 8.6)."""
        # The paren content is stripped leaving empty/junk segments only.
        result = _parse_song_title("(Official Remix)")
        self.assertIsNone(result)

    # --- Bare track (single segment, no artist) ---

    def test_bare_track_single_segment(self):
        """A single non-junk segment with no dash separator becomes a bare track."""
        result = _parse_song_title("Imagine")
        self.assertIsNotNone(result)
        self.assertEqual(result.track, "Imagine")
        self.assertEqual(result.artists, [])


# ---------------------------------------------------------------------------
# 4. TestParseSongTitleRealPlaylist
# ---------------------------------------------------------------------------

class TestParseSongTitleRealPlaylist(unittest.TestCase):
    """Parses a large raw-title fixture; also asserts specific track values (Req 8.8)."""

    RAW_TITLES = """
David Guetta - Titanium ft. Sia (Official Video)
Ellie Goulding - Bittersweet (Spectrum Remix)
Flight Facilities - Crave You (Adventure Club Dubstep Remix) (feat. Giselle)
Dubba Jonny - New Day
DJ Tiesto - Welcome to Ibiza ( HD [-Full-] )
Freestylers - Cracks ft. Belle Humble (Flux Pavilion Remix) HQ Full Extended Mix
Sub Focus - Turn Back Time
Sub Focus - Tidal Wave ft. Alpines
Ellie Goulding - Explosions (Gemini Remix)
Ellie Goulding - Figure 8 (Xilent Remix)
Example - Stay Awake (Moam Remix) (Official Audio) | Ministry of Sound
Dream - This Isn't House (Flinch Remix)
Linkin Park - Lost In The Echo (Killsonik Remix) [Recharged 2013] [HQ 1080p]
NERO 'PROMISES' (SKRILLEX AND NERO REMIX)
Skrillex &amp; Damian "Jr. Gong" Marley - Make It Bun Dem [OFFICIAL VIDEO]
Modestep - Another Day (Ft. Popeska) (xKore Remix) (Official Video)
Awolnation - Sail (Unlimited Gravity Dubstep Remix)
Adventure Club &amp; Krewella - Rise &amp; Fall
R3HAB &amp; KSHMR - Karate (CARTVNZ Festival Trap Remix)
[Hardcore] - Stonebank - Stronger (feat. EMEL) [Monstercat Release]
Jerk it out - The caesars
Band of Horses - The Funeral [OFFICIAL VIDEO]
ΑΜΜΟΧΩΣΤΟΣ - ΧΩΜΑ ΠΟΥ ΠΕΡΠΑΤΗΣΑ
Chris Brown - Don't Wake Me Up (Official Video)
Wiz Khalifa - Work Hard Play Hard [Music Video]
will.i.am - Scream &amp; Shout ft. Britney Spears
Ellie Goulding - Bittersweet (Spectrum Remix)
Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video)
Nicki Minaj - Pound The Alarm (Explicit)
Ke$ha - Die Young (Official Video)
Ellie Goulding - Hanging On (Sound Remedy Remix)
The Script - Hall of Fame (Official Video) ft. will.i.am
Paul Potts First Audition
Nirvana - Girls (Dj Dima House &amp; Samsonoff Remix)
Elix - Music Is My Therapy (Official Music Video)
Nicki Minaj - Fly ft. Rihanna
Eminem - Not Afraid
NERO 'PROMISES' (SKRILLEX AND NERO REMIX)
Avicii 'Levels' Skrillex Remix [FULL]
Mt Eden Dubstep - Sierra Leone [HD]
Greek swearing his head off! (Ανεστη εισαι μαλακας)
Private video
Big Time Rush - Windows Down (Official Video)
PSY - GANGNAM STYLE(강남스타일) M/V
Sienna Skies - Breathe
Flight Facilities - Crave You (Adventure Club Dubstep Remix) (feat. Giselle)
Mann - Buzzin (Remix) ft. 50 Cent
SKRILLEX - Bangarang feat. Sirah [Official Music Video]
Bob Sinclar - Rock the Boat feat. Pitbull, Dragonfly and Fatman Scoop [Official Video Clip]
Foster The People - Pumped Up Kicks (Official Video)
Rusko - Day N Night
Sean Paul - So Fine (Official Video)
Loreen - Euphoria (LIVE) | Sweden 🇸🇪 | Grand Final | Winner of Eurovision 2012
TUS feat. Remis Xantos - ΜΗ ΡΩΤΑΣ ΠΩΣ ΠΕΡΝΑΩ (SCHAU HIN) - Official Video Clip (HQ)
Imany - You Will Never Know (Clip Officiel)
Labrinth - Last Time
Flo Rida - Club Can't Handle Me (feat David Guetta) [Official Video]
Gym Class Heroes: Stereo Hearts ft. Adam Levine [OFFICIAL VIDEO]
Usher - More (RedOne Jimmy Joker Remix)
will.i.am - This Is Love ft. Eva Simons
Brian Cross - Soldier (Videoclip) ft. Daniel Gidlund
Kylie Minogue - Timebomb (Official Video)
The Wanted - Chasing The Sun
Tulisa - Young (Official Video)
Taio Cruz - There She Goes (Official Video) ft. Pitbull
Kasabian - Days Are Forgotten
Rihanna - Where Have You Been
Cheryl - Call My Name
Calvin Harris - Let's Go (Official Video) ft. Ne-Yo
Flo Rida - Whistle [Official Video]
Katy Perry - The One That Got Away (Official Music Video)
Fun.: We Are Young ft. Janelle Monáe [OFFICIAL VIDEO]
Antonis Remos feat Nivo - Entaksei [Official Music Video 2012 HD]
Amy Macdonald - This is the Life
Sea Of Smiles - Sienna Skies (lyrics)
Sean Paul - Got 2 Luv U (feat. Alexis Jordan) [Official Video]
Nayer - Suave (Kiss Me) ft. Pitbull, Mohombi
Ivi Adamou - La La Love (Cyprus) 2012 Eurovision Song Contest Official Preview Video
Swedish House Mafia - Greyhound
will.i.am - T.H.E. (The Hardest Ever) ft. Mick Jagger, Jennifer Lopez
The Black Eyed Peas - The Time (Dirty Bit) (Audio)
Flo Rida - Good Feeling [Official Video]
Aura Dione - Friends ft. Rock Mafia (Official Music Video)
Nelly Furtado - Big Hoops (Bigger The Better)
Nicki Minaj - Starships (Explicit) (Official Video)
The Wanted - Glad You Came
B.o.B - Airplanes (feat. Hayley Williams of Paramore) [Official Video]
Gravitonas - Lucky Star
Alyssa Reid - Alone Again
Jessie J - Laserlight ft. David Guetta (Official Video)
DEV - Naked ft. Enrique Iglesias
Kaiser Chiefs - Man On Mars (Official Video)
Flo Rida - Wild Ones (feat Sia) [Official Video]
Taio Cruz - Higher (Official UK Version) ft. Kylie Minogue
Pitbull - Hey Baby (Drop It To The Floor) ft. T-Pain
Madonna - Girl Gone Wild (Official Video)
PLAYMEN  - Fallin ft. Demy | Official Video Clip | Radio Edit
Maroon 5 - Payphone ft. Wiz Khalifa (Lyric Video)
Olly Murs - Heart Skips a Beat ft. Rizzle Kicks
Adrian Sina "Angel" feat. Sandra N - Angel (Official Video)
Kelly Clarkson - Stronger (What Doesn't Kill You) [Official Video]
PLAYMEN &amp; ALEX LEON ft. T-PAIN - Out Of My Head | Official Video Clip
Coldplay - Paradise (Official Video)
Rihanna - You Da One
Far East Movement - Like A G6 ft. The Cataracs, DEV
Labrinth - Earthquake (Official Video) ft. Tinie Tempah
Chris Brown - Turn Up the Music (Official Video)
Tacabro - Tacatà - Tacata'
Far East Movement - Live My Life (Party Rock Remix) ft. Justin Bieber, Redfoo
Example - 'Stay Awake' (Official Video)
Dubba Jonny - New Day
Lana Del Rey - Born To Die
Pitbull - International Love (Official Video) ft. Chris Brown
Gotye - Somebody That I Used To Know (feat. Kimbra) [Official Music Video]
Good Life- OneRepublic (cover) Megan Nicole and Alex Goot
U2 - Beautiful Day (Official Music Video)
Aggro Santos feat Kimberly Wyatt - Candy (Official Video)
Nelly Furtado - Night Is Young
Martin Solveig - One 2 3 Four [please watch it in high quality]
All Time Low - I Feel Like Dancin'
Grits - My Life Be Like (Ooh-Aah) with lyrics
Abandon All Ships - Take One Last Breath (Official Music Video)
David Guetta - Where Them Girls At ft. Nicki Minaj, Flo Rida (Official Video)
Taio Cruz - Hangover (Official Video) ft. Flo Rida
Avicii - Levels
Simon From Deep Divas feat. Goody - Disco Dancer [Simon Original Mix] [OFFICIAL VIDEO]
Christina Perri - Arms [Official Lyric Video]
Avril Lavigne - Wish You Were Here (Official Video)
Deleted video
David Guetta - Without You ft. Usher (Official Video)
Modestep - Sunlight (Official Video)
Lykke Li - I Follow Rivers (Director: Tarik Saleh)
Freestylers - Cracks ft. Belle Humble (Flux Pavilion Remix) HQ Full Extended Mix
Alesso &amp; Calvin Harris feat. Hurts - Under Control (Extended Mix)
[House] - Vicetone - Harmony [Monstercat Release] - New Artist Week Pt. 2
[DnB] - Tristam &amp; Braken - Frame of Mind [Monstercat Release]
[DnB] - Subformat - More (feat. Charli Brix) [Monstercat Release] - New Artist Week Pt. 2
[DnB] - Day One - White City [Monstercat Release]
[DnB] - Feint - Snake Eyes (feat. CoMa) [Monstercat Release]
[Drumstep] - Rogue - Dreams (Feat. Laura Brehm) [Monstercat EP Release]
[House] - Laszlo - Interstellar [Monstercat Release]
Private video
Otto Knows - Million Voices
David Guetta &amp; Showtek - Bad ft.Vassy (Lyrics Video)
New World Sound &amp; Thomas Newson - Flute (Original Mix)
Showtek ft. We Are Loud &amp; Sonny Wilson - Booyah (Official Music Video)
Hardwell feat. Amba Shepherd - Apollo (Radio Edit) - OUT NOW!
Bang La Decks - Utopia (Official Audio)
Astronaut - Rain (MitiS Remix)
K-391 - Summertime [Sunshine]
NERVO - Hold On (R3hab &amp; Silvio Ecomo Remix)
Major Lazer - Watch Out For This (Bumaye) (Dimitri Vegas &amp; Like Mike Tomorrowland Remix)
Steve Aoki, Chris Lake &amp; Tujamo - Boneless (Official Video)
Kid Cudi - Pursuit of Happiness (Steve Aoki Remix) - Project X (Official Music Video)
[House] - Vicetone - Heartbeat (feat. Collin McLoughlin) [Monstercat Release]
Meg &amp; Dia - Monster (DotEXE Dubstep Remix)
Private video
ENVY/Nico &amp; Vinz - Am I Wrong (Felix Zaltaio &amp; Lindh Van Berg Remix)
[Drumstep] - Rootkit - Against the Sun (feat. Anna Yvette) [Monstercat Release]
Hi-Rez - Smiling
Joywave - Tongues (feat. Kopps) (RAC Remix)
"""

    def setUp(self):
        titles_raw = [line.strip() for line in self.RAW_TITLES.splitlines() if line.strip()]
        self.titles = list(dict.fromkeys(titles_raw))
        self.null_titles = {"Private video", "Deleted video"}

    def test_all_titles_parse_non_null_or_are_known_null(self):
        """Every fixture title either parses to a non-empty result or is a known null entry."""
        for title in self.titles:
            with self.subTest(title=title):
                parsed = _parse_song_title(title)
                if title in self.null_titles:
                    self.assertIsNone(parsed)
                    continue
                self.assertIsNotNone(parsed)
                self.assertTrue(parsed.track.strip())

    def test_specific_track_values_for_known_good_titles(self):
        """Assert specific track values for at least 5 known-good titles (Req 8.8)."""
        known_good = [
            (
                "David Guetta - Titanium ft. Sia (Official Video)",
                "Titanium",
            ),
            (
                "Gotye - Somebody That I Used To Know (feat. Kimbra) [Official Music Video]",
                "Somebody That I Used To Know",
            ),
            (
                'Skrillex &amp; Damian "Jr. Gong" Marley - Make It Bun Dem [OFFICIAL VIDEO]',
                "Make It Bun Dem",
            ),
            (
                "Adventure Club &amp; Krewella - Rise &amp; Fall",
                "Rise & Fall",
            ),
            (
                "Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video)",
                "Don't You Worry Child",
            ),
        ]
        for title, expected_track in known_good:
            with self.subTest(title=title):
                parsed = _parse_song_title(title)
                self.assertIsNotNone(parsed, msg=f"Expected non-None for {title!r}")
                self.assertEqual(expected_track, parsed.track)


# ---------------------------------------------------------------------------
# 5. TestIsValidMatchTruePositives
# ---------------------------------------------------------------------------

class TestIsValidMatchTruePositives(unittest.TestCase):
    """Cases where _is_valid_match should return True."""

    def test_direct_artist_track_match(self):
        """Direct artist-track match: Queen / Bohemian Rhapsody."""
        search = _parse_song_title("Queen - Bohemian Rhapsody (Official Video)")
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "Bohemian Rhapsody - Remastered 2011", "artists": [{"name": "Queen"}]},
            )
        )

    def test_multi_word_artist_match(self):
        """Multi-word artist name: Miles Davis / So What."""
        search = _parse_song_title("Miles Davis - So What")
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "So What", "artists": [{"name": "Miles Davis"}]},
            )
        )

    def test_acronym_artist_match(self):
        """Acronym artist: BTS / Dynamite."""
        search = _parse_song_title("BTS - Dynamite")
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "Dynamite", "artists": [{"name": "BTS"}]},
            )
        )

    def test_reversed_format_swap_path(self):
        """Reversed/swap format: 'Take On Me - a-ha'."""
        search = _parse_song_title("Take On Me - a-ha")
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "Take On Me", "artists": [{"name": "a-ha"}]},
            )
        )

    def test_case_insensitive_match(self):
        """Case-insensitive match: 'bad guy' / Billie Eilish."""
        search = SongSearch(track="Bad Guy", artists=["Billie Eilish"])
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "bad guy", "artists": [{"name": "Billie Eilish"}]},
            )
        )

    def test_no_artist_search_matching_by_track_only(self):
        """No-artist SongSearch matches by track name alone: One More Time."""
        search = SongSearch(track="One More Time", artists=[])
        self.assertTrue(
            _is_valid_match(
                search,
                {"name": "One More Time (Radio Edit)", "artists": [{"name": "Daft Punk"}]},
            )
        )

    def test_topic_channel_resolves_correctly_via_swap_path(self):
        """Topic channel title resolves to the correct Spotify result via swap path."""
        search = _parse_song_title("Bohemian Rhapsody - Queen - Topic")
        spotify_track = {"name": "Bohemian Rhapsody", "artists": [{"name": "Queen"}]}
        self.assertIsNotNone(search)
        self.assertTrue(_is_valid_match(search, spotify_track))


# ---------------------------------------------------------------------------
# 6. TestIsValidMatchFalsePositives
# ---------------------------------------------------------------------------

class TestIsValidMatchFalsePositives(unittest.TestCase):
    """Cases where _is_valid_match should return False."""

    def test_wrong_artist(self):
        """Wrong artist: Linkin Park track vs Jay-Z on Spotify."""
        search = SongSearch(track="Numb", artists=["Linkin Park"])
        self.assertFalse(
            _is_valid_match(
                search,
                {"name": "Numb", "artists": [{"name": "Jay-Z"}]},
            )
        )

    def test_wrong_track(self):
        """Wrong track: 'One More Time' search vs a completely different Spotify track."""
        search = SongSearch(track="One More Time", artists=[])
        self.assertFalse(
            _is_valid_match(
                search,
                {"name": "Harder Better Faster Stronger", "artists": [{"name": "Daft Punk"}]},
            )
        )

    def test_partial_track_name(self):
        """Partial track name: 'Take On Me' must not match Spotify track 'On Me'."""
        search = SongSearch(track="Take On Me", artists=["a-ha"])
        self.assertFalse(
            _is_valid_match(
                search,
                {"name": "On Me", "artists": [{"name": "a-ha"}]},
            )
        )

    def test_short_token_false_positive(self):
        """Short-token guard (Req 8.5): 'One' by Metallica must not match 'One More Time'."""
        search = SongSearch(track="One", artists=["Metallica"])
        self.assertFalse(
            _is_valid_match(
                search,
                {"name": "One More Time", "artists": [{"name": "Daft Punk"}]},
            )
        )


if __name__ == "__main__":
    unittest.main()
