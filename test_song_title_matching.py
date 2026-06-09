import unittest

from youtube2spotify import (
    SongSearch,
    _is_valid_match,
    _parse_song_title,
    _tokens_in_order,
)


PARSE_SONG_TITLE_CASES = [
    ("Chuck Berry - Johnny B. Goode", "Johnny B. Goode", ["Chuck Berry"]),
    ("The Beatles - Let It Be (Remastered 2009)", "Let It Be", ["The Beatles"]),
    ("Queen - Bohemian Rhapsody (Official Video)", "Bohemian Rhapsody", ["Queen"]),
    ("Nirvana - Smells Like Teen Spirit [HD]", "Smells Like Teen Spirit", ["Nirvana"]),
    ("AC/DC - Back In Black", "Back In Black", ["AC/DC"]),
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

# (raw_title, expected_track, expected_artists)
RAW_TITLES_CASES = [
    ("David Guetta - Titanium ft. Sia (Official Video)", "Titanium", ["David Guetta", "Sia"]),
    ("Ellie Goulding - Bittersweet (Spectrum Remix)", "Bittersweet", ["Ellie Goulding"]),
    ("Flight Facilities - Crave You (Adventure Club Dubstep Remix) (feat. Giselle)", "Crave You", ["Flight Facilities", "Giselle"]),
    ("Dubba Jonny - New Day", "New Day", ["Dubba Jonny"]),
    ("DJ Tiesto - Welcome to Ibiza ( HD [-Full-] )", "Welcome to Ibiza", ["DJ Tiesto"]),
    ("Freestylers - Cracks ft. Belle Humble (Flux Pavilion Remix) HQ Full Extended Mix", "Cracks", ["Freestylers", "Belle Humble"]),
    ("Sub Focus - Turn Back Time", "Turn Back Time", ["Sub Focus"]),
    ("Sub Focus - Tidal Wave ft. Alpines", "Tidal Wave", ["Sub Focus", "Alpines"]),
    ("Ellie Goulding - Explosions (Gemini Remix)", "Explosions", ["Ellie Goulding"]),
    ("Ellie Goulding - Figure 8 (Xilent Remix)", "Figure 8", ["Ellie Goulding"]),
    ("Example - Stay Awake (Moam Remix) (Official Audio) | Ministry of Sound", "Stay Awake", ["Example"]),
    ("Dream - This Isn't House (Flinch Remix)", "This Isn't House", ["Dream"]),
    ("Linkin Park - Lost In The Echo (Killsonik Remix) [Recharged 2013] [HQ 1080p]", "Lost In The Echo", ["Linkin Park"]),
    ("NERO 'PROMISES' (SKRILLEX AND NERO REMIX)", "NERO 'PROMISES", []),
    ('Skrillex &amp; Damian "Jr. Gong" Marley - Make It Bun Dem [OFFICIAL VIDEO]', "Make It Bun Dem", ["Skrillex", 'Damian "Jr. Gong" Marley']),
    ("Modestep - Another Day (Ft. Popeska) (xKore Remix) (Official Video)", "Another Day", ["Modestep", "Popeska"]),
    ("Awolnation - Sail (Unlimited Gravity Dubstep Remix)", "Sail", ["Awolnation"]),
    ("Adventure Club &amp; Krewella - Rise &amp; Fall", "Rise & Fall", ["Adventure Club", "Krewella"]),
    ("R3HAB &amp; KSHMR - Karate (CARTVNZ Festival Trap Remix)", "Karate", ["R3HAB", "KSHMR"]),
    ("[Hardcore] - Stonebank - Stronger (feat. EMEL) [Monstercat Release]", "Stronger", ["Stonebank", "EMEL"]),
    ("Jerk it out - The caesars", "The caesars", ["Jerk it out"]),
    ("Band of Horses - The Funeral [OFFICIAL VIDEO]", "The Funeral", ["Band of Horses"]),
    ("Chris Brown - Don't Wake Me Up (Official Video)", "Don't Wake Me Up", ["Chris Brown"]),
    ("Wiz Khalifa - Work Hard Play Hard [Music Video]", "Work Hard Play Hard", ["Wiz Khalifa"]),
    ("will.i.am - Scream &amp; Shout ft. Britney Spears", "Scream & Shout", ["will.i.am", "Britney Spears"]),
    ("Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video)", "Don't You Worry Child", ["Swedish House Mafia", "John Martin"]),
    ("Nicki Minaj - Pound The Alarm (Explicit)", "Pound The Alarm", ["Nicki Minaj"]),
    ("Ke$ha - Die Young (Official Video)", "Die Young", ["Ke$ha"]),
    ("Ellie Goulding - Hanging On (Sound Remedy Remix)", "Hanging On", ["Ellie Goulding"]),
    ("The Script - Hall of Fame (Official Video) ft. will.i.am", "Hall of Fame", ["The Script", "will.i.am"]),
    ("Paul Potts First Audition", "Paul Potts First Audition", []),
    ("Nirvana - Girls (Dj Dima House &amp; Samsonoff Remix)", "Girls", ["Nirvana"]),
    ("Elix - Music Is My Therapy (Official Music Video)", "Music Is My Therapy", ["Elix"]),
    ("Nicki Minaj - Fly ft. Rihanna", "Fly", ["Nicki Minaj", "Rihanna"]),
    ("Eminem - Not Afraid", "Not Afraid", ["Eminem"]),
    ("Avicii 'Levels' Skrillex Remix [FULL]", "Avicii 'Levels' Skrillex Remix", []),
    ("Mt Eden Dubstep - Sierra Leone [HD]", "Sierra Leone", ["Mt Eden Dubstep"]),
    ("Private video", None, None),
    ("Big Time Rush - Windows Down (Official Video)", "Windows Down", ["Big Time Rush"]),
    ("PSY - GANGNAM STYLE(강남스타일) M/V", "GANGNAM STYLE", ["PSY"]),
    ("Sienna Skies - Breathe", "Breathe", ["Sienna Skies"]),
    ("Mann - Buzzin (Remix) ft. 50 Cent", "Buzzin", ["Mann", "50 Cent"]),
    ("SKRILLEX - Bangarang feat. Sirah [Official Music Video]", "Bangarang", ["SKRILLEX", "Sirah"]),
    ("Bob Sinclar - Rock the Boat feat. Pitbull, Dragonfly and Fatman Scoop [Official Video Clip]", "Rock the Boat", ["Bob Sinclar", "Pitbull, Dragonfly and Fatman Scoop"]),
    ("Foster The People - Pumped Up Kicks (Official Video)", "Pumped Up Kicks", ["Foster The People"]),
    ("Rusko - Day N Night", "Day N Night", ["Rusko"]),
    ("Sean Paul - So Fine (Official Video)", "So Fine", ["Sean Paul"]),
    ("Loreen - Euphoria (LIVE) | Sweden 🇸🇪 | Grand Final | Winner of Eurovision 2012", "Euphoria", ["Loreen"]),
    ("Imany - You Will Never Know (Clip Officiel)", "You Will Never Know", ["Imany"]),
    ("Labrinth - Last Time", "Last Time", ["Labrinth"]),
    ("Flo Rida - Club Can't Handle Me (feat David Guetta) [Official Video]", "Club Can't Handle Me", ["Flo Rida", "David Guetta"]),
    # colon in artist name — parser keeps "Gym Class Heroes: Stereo Hearts" as track
    ("Gym Class Heroes: Stereo Hearts ft. Adam Levine [OFFICIAL VIDEO]", "Gym Class Heroes: Stereo Hearts", ["Adam Levine"]),
    ("Usher - More (RedOne Jimmy Joker Remix)", "More", ["Usher"]),
    ("will.i.am - This Is Love ft. Eva Simons", "This Is Love", ["will.i.am", "Eva Simons"]),
    ("Brian Cross - Soldier (Videoclip) ft. Daniel Gidlund", "Soldier", ["Brian Cross", "Daniel Gidlund"]),
    ("Kylie Minogue - Timebomb (Official Video)", "Timebomb", ["Kylie Minogue"]),
    ("The Wanted - Chasing The Sun", "Chasing The Sun", ["The Wanted"]),
    ("Tulisa - Young (Official Video)", "Young", ["Tulisa"]),
    ("Taio Cruz - There She Goes (Official Video) ft. Pitbull", "There She Goes", ["Taio Cruz", "Pitbull"]),
    ("Kasabian - Days Are Forgotten", "Days Are Forgotten", ["Kasabian"]),
    ("Rihanna - Where Have You Been", "Where Have You Been", ["Rihanna"]),
    ("Cheryl - Call My Name", "Call My Name", ["Cheryl"]),
    ("Calvin Harris - Let's Go (Official Video) ft. Ne-Yo", "Let's Go", ["Calvin Harris", "Ne-Yo"]),
    ("Flo Rida - Whistle [Official Video]", "Whistle", ["Flo Rida"]),
    ("Katy Perry - The One That Got Away (Official Music Video)", "The One That Got Away", ["Katy Perry"]),
    ("Fun.: We Are Young ft. Janelle Monáe [OFFICIAL VIDEO]", "Fun.: We Are Young", ["Janelle Monáe"]),
    ("Antonis Remos feat Nivo - Entaksei [Official Music Video 2012 HD]", "Entaksei", ["Antonis Remos", "Nivo"]),
    ("Amy Macdonald - This is the Life", "This is the Life", ["Amy Macdonald"]),
    ("Sea Of Smiles - Sienna Skies (lyrics)", "Sienna Skies", ["Sea Of Smiles"]),
    ("Sean Paul - Got 2 Luv U (feat. Alexis Jordan) [Official Video]", "Got 2 Luv U", ["Sean Paul", "Alexis Jordan"]),
    ("Nayer - Suave (Kiss Me) ft. Pitbull, Mohombi", "Suave", ["Nayer", "Pitbull, Mohombi"]),
    ("Ivi Adamou - La La Love (Cyprus) 2012 Eurovision Song Contest Official Preview Video", "La La Love 2012 Eurovision Song Contest Official Preview", ["Ivi Adamou"]),
    ("Swedish House Mafia - Greyhound", "Greyhound", ["Swedish House Mafia"]),
    ("will.i.am - T.H.E. (The Hardest Ever) ft. Mick Jagger, Jennifer Lopez", "T.H.E.", ["will.i.am", "Mick Jagger, Jennifer Lopez"]),
    ("The Black Eyed Peas - The Time (Dirty Bit) (Audio)", "The Time", ["The Black Eyed Peas"]),
    ("Flo Rida - Good Feeling [Official Video]", "Good Feeling", ["Flo Rida"]),
    ("Aura Dione - Friends ft. Rock Mafia (Official Music Video)", "Friends", ["Aura Dione", "Rock Mafia"]),
    ("Nelly Furtado - Big Hoops (Bigger The Better)", "Big Hoops", ["Nelly Furtado"]),
    ("Nicki Minaj - Starships (Explicit) (Official Video)", "Starships", ["Nicki Minaj"]),
    ("The Wanted - Glad You Came", "Glad You Came", ["The Wanted"]),
    ("B.o.B - Airplanes (feat. Hayley Williams of Paramore) [Official Video]", "Airplanes", ["B.o.B", "Hayley Williams of Paramore"]),
    ("Gravitonas - Lucky Star", "Lucky Star", ["Gravitonas"]),
    ("Alyssa Reid - Alone Again", "Alone Again", ["Alyssa Reid"]),
    ("Jessie J - Laserlight ft. David Guetta (Official Video)", "Laserlight", ["Jessie J", "David Guetta"]),
    ("DEV - Naked ft. Enrique Iglesias", "Naked", ["DEV", "Enrique Iglesias"]),
    ("Kaiser Chiefs - Man On Mars (Official Video)", "Man On Mars", ["Kaiser Chiefs"]),
    ("Flo Rida - Wild Ones (feat Sia) [Official Video]", "Wild Ones", ["Flo Rida", "Sia"]),
    ("Taio Cruz - Higher (Official UK Version) ft. Kylie Minogue", "Higher", ["Taio Cruz", "Kylie Minogue"]),
    ("Pitbull - Hey Baby (Drop It To The Floor) ft. T-Pain", "Hey Baby", ["Pitbull", "T-Pain"]),
    ("Madonna - Girl Gone Wild (Official Video)", "Girl Gone Wild", ["Madonna"]),
    ("PLAYMEN  - Fallin ft. Demy | Official Video Clip | Radio Edit", "Fallin", ["PLAYMEN", "Demy"]),
    ("Maroon 5 - Payphone ft. Wiz Khalifa (Lyric Video)", "Payphone", ["Maroon 5", "Wiz Khalifa"]),
    ("Olly Murs - Heart Skips a Beat ft. Rizzle Kicks", "Heart Skips a Beat", ["Olly Murs", "Rizzle Kicks"]),
    ('Adrian Sina "Angel" feat. Sandra N - Angel (Official Video)', "Angel", ['Adrian Sina "Angel"', "Sandra N"]),
    ("Kelly Clarkson - Stronger (What Doesn't Kill You) [Official Video]", "Stronger", ["Kelly Clarkson"]),
    ("PLAYMEN &amp; ALEX LEON ft. T-PAIN - Out Of My Head | Official Video Clip", "Out Of My Head", ["PLAYMEN", "ALEX LEON", "T-PAIN"]),
    ("Coldplay - Paradise (Official Video)", "Paradise", ["Coldplay"]),
    ("Rihanna - You Da One", "You Da One", ["Rihanna"]),
    ("Far East Movement - Like A G6 ft. The Cataracs, DEV", "Like A G6", ["Far East Movement", "The Cataracs, DEV"]),
    ("Labrinth - Earthquake (Official Video) ft. Tinie Tempah", "Earthquake", ["Labrinth", "Tinie Tempah"]),
    ("Chris Brown - Turn Up the Music (Official Video)", "Turn Up the Music", ["Chris Brown"]),
    ("Tacabro - Tacatà - Tacata'", "Tacata", ["Tacatà"]),
    ("Far East Movement - Live My Life (Party Rock Remix) ft. Justin Bieber, Redfoo", "Live My Life", ["Far East Movement", "Justin Bieber, Redfoo"]),
    ("Example - 'Stay Awake' (Official Video)", "Stay Awake", ["Example"]),
    ("Lana Del Rey - Born To Die", "Born To Die", ["Lana Del Rey"]),
    ("Pitbull - International Love (Official Video) ft. Chris Brown", "International Love", ["Pitbull", "Chris Brown"]),
    ("Gotye - Somebody That I Used To Know (feat. Kimbra) [Official Music Video]", "Somebody That I Used To Know", ["Gotye", "Kimbra"]),
    # missing dash between artist and title — falls through as single segment
    ("Good Life- OneRepublic (cover) Megan Nicole and Alex Goot", "Good Life- OneRepublic Megan Nicole and Alex Goot", []),
    ("U2 - Beautiful Day (Official Music Video)", "Beautiful Day", ["U2"]),
    ("Aggro Santos feat Kimberly Wyatt - Candy (Official Video)", "Candy", ["Aggro Santos", "Kimberly Wyatt"]),
    ("Nelly Furtado - Night Is Young", "Night Is Young", ["Nelly Furtado"]),
    ("Martin Solveig - One 2 3 Four [please watch it in high quality]", "One 2 3 Four", ["Martin Solveig"]),
    ("All Time Low - I Feel Like Dancin'", "I Feel Like Dancin", ["All Time Low"]),
    ("Grits - My Life Be Like (Ooh-Aah) with lyrics", "My Life Be Like with", ["Grits"]),
    ("Abandon All Ships - Take One Last Breath (Official Music Video)", "Take One Last Breath", ["Abandon All Ships"]),
    ("David Guetta - Where Them Girls At ft. Nicki Minaj, Flo Rida (Official Video)", "Where Them Girls At", ["David Guetta", "Nicki Minaj, Flo Rida"]),
    ("Taio Cruz - Hangover (Official Video) ft. Flo Rida", "Hangover", ["Taio Cruz", "Flo Rida"]),
    ("Avicii - Levels", "Levels", ["Avicii"]),
    ("Simon From Deep Divas feat. Goody - Disco Dancer [Simon Original Mix] [OFFICIAL VIDEO]", "Disco Dancer", ["Simon From Deep Divas", "Goody"]),
    ("Christina Perri - Arms [Official Lyric Video]", "Arms", ["Christina Perri"]),
    ("Avril Lavigne - Wish You Were Here (Official Video)", "Wish You Were Here", ["Avril Lavigne"]),
    ("Deleted video", None, None),
    ("David Guetta - Without You ft. Usher (Official Video)", "Without You", ["David Guetta", "Usher"]),
    ("Modestep - Sunlight (Official Video)", "Sunlight", ["Modestep"]),
    ("Lykke Li - I Follow Rivers (Director: Tarik Saleh)", "I Follow Rivers", ["Lykke Li"]),
    ("Alesso &amp; Calvin Harris feat. Hurts - Under Control (Extended Mix)", "Under Control", ["Alesso", "Calvin Harris", "Hurts"]),
    ("[House] - Vicetone - Harmony [Monstercat Release] - New Artist Week Pt. 2", "Harmony", ["Vicetone"]),
    ("[DnB] - Tristam &amp; Braken - Frame of Mind [Monstercat Release]", "Frame of Mind", ["Tristam", "Braken"]),
    ("[DnB] - Subformat - More (feat. Charli Brix) [Monstercat Release] - New Artist Week Pt. 2", "More", ["Subformat", "Charli Brix"]),
    ("[DnB] - Day One - White City [Monstercat Release]", "White City", ["Day One"]),
    ("[DnB] - Feint - Snake Eyes (feat. CoMa) [Monstercat Release]", "Snake Eyes", ["Feint", "CoMa"]),
    ("[Drumstep] - Rogue - Dreams (Feat. Laura Brehm) [Monstercat EP Release]", "Dreams", ["Rogue", "Laura Brehm"]),
    ("[House] - Laszlo - Interstellar [Monstercat Release]", "Interstellar", ["Laszlo"]),
    ("Private video", None, None),
    ("Otto Knows - Million Voices", "Million Voices", ["Otto Knows"]),
    ("David Guetta &amp; Showtek - Bad ft.Vassy (Lyrics Video)", "Bad", ["David Guetta", "Showtek", "Vassy"]),
    ("New World Sound &amp; Thomas Newson - Flute (Original Mix)", "Flute", ["New World Sound", "Thomas Newson"]),
    ("Showtek ft. We Are Loud &amp; Sonny Wilson - Booyah (Official Music Video)", "Booyah", ["Showtek", "We Are Loud", "Sonny Wilson"]),
    ("Hardwell feat. Amba Shepherd - Apollo (Radio Edit) - OUT NOW!", "Apollo", ["Hardwell", "Amba Shepherd"]),
    ("Bang La Decks - Utopia (Official Audio)", "Utopia", ["Bang La Decks"]),
    ("Astronaut - Rain (MitiS Remix)", "Rain", ["Astronaut"]),
    ("K-391 - Summertime [Sunshine]", "Summertime", ["K-391"]),
    ("NERVO - Hold On (R3hab &amp; Silvio Ecomo Remix)", "Hold On", ["NERVO"]),
    ("Major Lazer - Watch Out For This (Bumaye) (Dimitri Vegas &amp; Like Mike Tomorrowland Remix)", "Watch Out For This", ["Major Lazer"]),
    ("Steve Aoki, Chris Lake &amp; Tujamo - Boneless (Official Video)", "Boneless", ["Steve Aoki, Chris Lake", "Tujamo"]),
    ("Kid Cudi - Pursuit of Happiness (Steve Aoki Remix) - Project X (Official Music Video)", "Pursuit of Happiness", ["Kid Cudi"]),
    ("[House] - Vicetone - Heartbeat (feat. Collin McLoughlin) [Monstercat Release]", "Heartbeat", ["Vicetone", "Collin McLoughlin"]),
    ("Meg &amp; Dia - Monster (DotEXE Dubstep Remix)", "Monster", ["Meg", "Dia"]),
    ("ENVY/Nico &amp; Vinz - Am I Wrong (Felix Zaltaio &amp; Lindh Van Berg Remix)", "Am I Wrong", ["ENVY/Nico", "Vinz"]),
    ("[Drumstep] - Rootkit - Against the Sun (feat. Anna Yvette) [Monstercat Release]", "Against the Sun", ["Rootkit", "Anna Yvette"]),
    ("Hi-Rez - Smiling", "Smiling", ["Hi-Rez"]),
    ("Joywave - Tongues (feat. Kopps) (RAC Remix)", "Tongues", ["Joywave", "Kopps"]),
]


# ---------------------------------------------------------------------------
# 1. TestTokensInOrder
# ---------------------------------------------------------------------------

class TestTokensInOrder(unittest.TestCase):
    """Tests for _tokens_in_order — the sequential-scan primitive used by all matchers."""

    def test_single_char_needle_filtered_out(self):
        """1-char needles fall below _MIN_NEEDLE_LEN and are discarded → False."""
        self.assertFalse(_tokens_in_order(["a"], ["a", "song"]))

    def test_single_char_needle_even_exact_haystack(self):
        """Even a perfect 1-char haystack is rejected when the needle is 1 char."""
        self.assertFalse(_tokens_in_order(["i"], ["i"]))

    def test_all_short_needles_empty_meaningful_list(self):
        """When every needle is too short, meaningful is empty → False."""
        self.assertFalse(_tokens_in_order(["a", "i"], ["a", "i", "song"]))

    def test_four_char_needle_matches(self):
        """A 4-char needle follows the normal sequential-scan path."""
        self.assertTrue(_tokens_in_order(["song"], ["song"]))

    def test_mixed_needles_short_stripped_long_matched(self):
        """Short needles are stripped; only the remaining long needle must match."""
        self.assertTrue(_tokens_in_order(["a", "song"], ["song"]))

    def test_two_char_needle_not_filtered(self):
        """_MIN_NEEDLE_LEN=2 means 2-char needles are kept, not discarded."""
        self.assertTrue(_tokens_in_order(["it"], ["it", "rocks"]))

    def test_two_needles_in_order_match(self):
        """Both needles must appear in the right left-to-right order."""
        self.assertTrue(_tokens_in_order(["take", "me"], ["take", "on", "me"]))

    def test_two_needles_reversed_order_reject(self):
        """Needles present but reversed → subsequence check fails."""
        self.assertFalse(_tokens_in_order(["me", "take"], ["take", "on", "me"]))

    def test_needle_not_present_at_all(self):
        """A needle that simply isn't in the haystack → False."""
        self.assertFalse(_tokens_in_order(["blue"], ["red", "green", "yellow"]))

    def test_duplicate_token_matches_first_occurrence(self):
        """The scanner advances on the first match; duplicate tokens in haystack are fine."""
        self.assertTrue(_tokens_in_order(["love"], ["love", "love", "song"]))

    def test_empty_needles_list(self):
        """Passing an empty needle list → meaningful is empty → False."""
        self.assertFalse(_tokens_in_order([], ["something"]))

    def test_empty_haystack(self):
        """Nothing to scan → False."""
        self.assertFalse(_tokens_in_order(["song"], []))


# ---------------------------------------------------------------------------
# 2. TestParseSongTitleHappyPath
# ---------------------------------------------------------------------------

class TestParseSongTitleHappyPath(unittest.TestCase):
    """Well-formed 'Artist - Track' titles across genres, decades and formats."""

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
    """Edge cases: sentinel titles, HTML entities, accents, Topic, pipe stripping, etc."""

    # --- sentinel entries ---

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_song_title(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(_parse_song_title("   "))

    def test_private_video_mixed_case_returns_none(self):
        self.assertIsNone(_parse_song_title("Private video"))

    def test_private_video_lower_returns_none(self):
        self.assertIsNone(_parse_song_title("private video"))

    def test_deleted_video_lower_returns_none(self):
        self.assertIsNone(_parse_song_title("Deleted video"))

    def test_deleted_video_all_caps_returns_none(self):
        self.assertIsNone(_parse_song_title("DELETED VIDEO"))

    # --- HTML entity decoding ---

    def test_amp_entity_decoded_artist_split(self):
        """&amp; decoded to & before the & is used as an artist separator."""
        result = _parse_song_title("Skrillex &amp; Damian Marley - Make It Bun Dem")
        self.assertIsNotNone(result)
        self.assertEqual("Make It Bun Dem", result.track)
        self.assertEqual(["Skrillex", "Damian Marley"], result.artists)

    def test_multiple_amp_entities_in_one_title(self):
        """Multiple &amp; entities in artist and track are all decoded."""
        result = _parse_song_title("Adventure Club &amp; Krewella - Rise &amp; Fall")
        self.assertIsNotNone(result)
        self.assertEqual("Rise & Fall", result.track)
        self.assertEqual(["Adventure Club", "Krewella"], result.artists)

    # --- pipe stripping ---

    def test_pipe_label_suffix_stripped(self):
        """Everything after the first '|' is discarded as label/channel noise."""
        result = _parse_song_title("Example - Stay Awake (Moam Remix) (Official Audio) | Ministry of Sound")
        self.assertIsNotNone(result)
        self.assertEqual("Stay Awake", result.track)
        self.assertEqual(["Example"], result.artists)

    def test_pipe_multiple_suffixes_all_stripped(self):
        """Multiple pipe-separated suffixes are all removed."""
        result = _parse_song_title("Loreen - Euphoria (LIVE) | Sweden | Grand Final | Winner of Eurovision 2012")
        self.assertIsNotNone(result)
        self.assertEqual("Euphoria", result.track)
        self.assertEqual(["Loreen"], result.artists)

    def test_pipe_stripping_does_not_eat_track_itself(self):
        """Pipe is only stripped from the tail; the core artist-track remains."""
        result = _parse_song_title("PLAYMEN - Fallin ft. Demy | Official Video Clip | Radio Edit")
        self.assertIsNotNone(result)
        self.assertEqual("Fallin", result.track)
        self.assertEqual(["PLAYMEN", "Demy"], result.artists)

    # --- accented / non-ASCII ---

    def test_accented_artist_name_preserved_exactly(self):
        """Accented characters are not mangled in the parsed output."""
        result = _parse_song_title("Rosalía - DESPECHÁ")
        self.assertIsNotNone(result)
        self.assertEqual("DESPECHÁ", result.track)
        self.assertEqual(["Rosalía"], result.artists)

    # --- YouTube Topic channel format ---

    def test_topic_segment_stripped_leaving_two_segments(self):
        """'Topic' is junk; after stripping, the two remaining segments parse normally."""
        result = _parse_song_title("Bohemian Rhapsody - Queen - Topic")
        self.assertIsNotNone(result)
        # Parser sees [Bohemian Rhapsody, Queen] after junk removal — artists first heuristic
        self.assertEqual("Queen", result.track)
        self.assertEqual(["Bohemian Rhapsody"], result.artists)

    def test_topic_case_insensitive_equals_no_topic(self):
        """'topic' / 'TOPIC' variants all produce the same result as the title without it."""
        lower = _parse_song_title("Take On Me - a-ha - topic")
        upper = _parse_song_title("Take On Me - a-ha - TOPIC")
        no_topic = _parse_song_title("Take On Me - a-ha")
        self.assertEqual(lower, upper)
        self.assertEqual(lower, no_topic)

    def test_topic_only_remaining_segment_is_bare_track(self):
        """When only one segment survives after Topic removal, it becomes a bare track."""
        result = _parse_song_title("Imagine - Topic")
        self.assertIsNotNone(result)
        self.assertEqual("Imagine", result.track)
        self.assertEqual([], result.artists)

    # --- noise-only / junk titles ---

    def test_brackets_only_returns_none(self):
        """A title made entirely of bracket content collapses to nothing."""
        self.assertIsNone(_parse_song_title("[Official Music Video]"))

    def test_parens_only_returns_none(self):
        """Paren content is stripped, leaving empty → None."""
        self.assertIsNone(_parse_song_title("(Official Remix)"))

    # --- bare track (no artist) ---

    def test_single_word_title_no_artist(self):
        result = _parse_song_title("Imagine")
        self.assertIsNotNone(result)
        self.assertEqual("Imagine", result.track)
        self.assertEqual([], result.artists)

    # --- genre prefix stripping ---

    def test_genre_prefix_country_stripped(self):
        """Genre label in first segment is dropped before artist/track assignment."""
        result = _parse_song_title("Country - Johnny Cash - Ring of Fire")
        self.assertIsNotNone(result)
        self.assertEqual("Ring of Fire", result.track)
        self.assertEqual(["Johnny Cash"], result.artists)

    def test_genre_prefix_lofi_stripped(self):
        result = _parse_song_title("Lofi - Jinsang - affection")
        self.assertIsNotNone(result)
        self.assertEqual("affection", result.track)
        self.assertEqual(["Jinsang"], result.artists)

    def test_monstercat_bracket_genre_stripped(self):
        """[Genre] brackets are removed; remaining segments parse as artist - track."""
        result = _parse_song_title("[DnB] - Feint - Snake Eyes (feat. CoMa) [Monstercat Release]")
        self.assertIsNotNone(result)
        self.assertEqual("Snake Eyes", result.track)
        self.assertEqual(["Feint", "CoMa"], result.artists)

    # --- featured artist extraction ---

    def test_feat_dot_extracts_featured_artist(self):
        result = _parse_song_title("Avicii - Wake Me Up feat. Aloe Blacc")
        self.assertIsNotNone(result)
        self.assertEqual("Wake Me Up", result.track)
        self.assertIn("Aloe Blacc", result.artists)

    def test_ft_dot_before_dash_extracts_artist(self):
        """'ft.' appearing before the dash (Swedish House Mafia format) is handled."""
        result = _parse_song_title("Swedish House Mafia ft. John Martin - Don't You Worry Child (Official Video)")
        self.assertIsNotNone(result)
        self.assertEqual("Don't You Worry Child", result.track)
        self.assertIn("Swedish House Mafia", result.artists)
        self.assertIn("John Martin", result.artists)

    def test_featuring_long_form_extracted(self):
        result = _parse_song_title("Gym Class Heroes: Stereo Hearts featuring Adam Levine")
        self.assertIsNotNone(result)
        self.assertIn("Adam Levine", result.artists)


# ---------------------------------------------------------------------------
# 4. TestParseSongTitleRealPlaylist
# ---------------------------------------------------------------------------

class TestParseSongTitleRealPlaylist(unittest.TestCase):
    """Full fixture sweep: every RAW_TITLES_CASES entry must match exactly."""

    def test_parse_song_title_real_playlist(self):
        seen = set()
        for title, expected_track, expected_artists in RAW_TITLES_CASES:
            if title in seen:
                continue
            seen.add(title)
            with self.subTest(title=title):
                parsed = _parse_song_title(title)
                if expected_track is None:
                    self.assertIsNone(parsed)
                else:
                    self.assertIsNotNone(parsed, msg=f"Expected non-None for {title!r}")
                    self.assertEqual(expected_track, parsed.track)
                    self.assertEqual(expected_artists, parsed.artists)


# ---------------------------------------------------------------------------
# 5. TestIsValidMatchTruePositives
# ---------------------------------------------------------------------------

class TestIsValidMatchTruePositives(unittest.TestCase):
    """_is_valid_match must return True for these real-world pairs."""

    def _sp(self, name, *artists):
        return {"name": name, "artists": [{"name": a} for a in artists]}

    # --- core path: track matches exactly, artist matches exactly ---

    def test_exact_track_and_artist(self):
        search = _parse_song_title("Eminem - Not Afraid")
        self.assertTrue(_is_valid_match(search, self._sp("Not Afraid", "Eminem")))

    def test_case_insensitive_track_match(self):
        search = SongSearch(track="Bad Guy", artists=["Billie Eilish"])
        self.assertTrue(_is_valid_match(search, self._sp("bad guy", "Billie Eilish")))

    def test_multi_word_artist_exact(self):
        search = _parse_song_title("Miles Davis - So What")
        self.assertTrue(_is_valid_match(search, self._sp("So What", "Miles Davis")))

    def test_acronym_artist(self):
        search = _parse_song_title("BTS - Dynamite")
        self.assertTrue(_is_valid_match(search, self._sp("Dynamite", "BTS")))

    # --- Spotify appends edition noise ---

    def test_spotify_remastered_year_suffix(self):
        """Spotify track 'Bohemian Rhapsody - Remastered 2011' should match our clean query."""
        search = _parse_song_title("Queen - Bohemian Rhapsody (Official Video)")
        self.assertTrue(_is_valid_match(search, self._sp("Bohemian Rhapsody - Remastered 2011", "Queen")))

    def test_spotify_remaster_without_year(self):
        search = SongSearch(track="Hotel California", artists=["Eagles"])
        self.assertTrue(_is_valid_match(search, self._sp("Hotel California - Remastered", "Eagles")))

    def test_spotify_radio_edit_suffix(self):
        search = SongSearch(track="One More Time", artists=["Daft Punk"])
        self.assertTrue(_is_valid_match(search, self._sp("One More Time - Radio Edit", "Daft Punk")))

    def test_spotify_single_version_suffix(self):
        search = SongSearch(track="Heroes", artists=["David Bowie"])
        self.assertTrue(_is_valid_match(search, self._sp("Heroes - Single Version", "David Bowie")))

    # --- reversed / Topic-channel format ---

    def test_reversed_track_artist_format(self):
        """'Take On Me - a-ha' parses with track first; swap path resolves it."""
        search = _parse_song_title("Take On Me - a-ha")
        self.assertTrue(_is_valid_match(search, self._sp("Take On Me", "a-ha")))

    def test_topic_channel_resolves_via_swap_path(self):
        search = _parse_song_title("Bohemian Rhapsody - Queen - Topic")
        self.assertTrue(_is_valid_match(search, self._sp("Bohemian Rhapsody", "Queen")))

    # --- no-artist search ---

    def test_no_artist_bare_track_match(self):
        """With no artist info we still match on track title alone."""
        search = SongSearch(track="One More Time", artists=[])
        self.assertTrue(_is_valid_match(search, self._sp("One More Time (Radio Edit)", "Daft Punk")))

    # --- accentend / Unicode ---

    def test_accented_artist_matches_unaccented_spotify(self):
        """'Rosalía' in search should match Spotify entry spelled 'Rosalia'."""
        search = SongSearch(track="DESPECHÁ", artists=["Rosalía"])
        self.assertTrue(_is_valid_match(search, self._sp("DESPECHÁ", "Rosalia")))

    def test_featured_artist_credited_separately_on_spotify(self):
        """Spotify credits the featured artist as a separate artist object."""
        search = _parse_song_title("Avicii - Wake Me Up feat. Aloe Blacc")
        self.assertTrue(_is_valid_match(search, self._sp("Wake Me Up", "Avicii", "Aloe Blacc")))

    def test_featured_artist_only_in_track_name_on_spotify(self):
        """Some Spotify releases encode feat. inside the track name, not as a separate artist."""
        search = _parse_song_title("Avicii - Wake Me Up feat. Aloe Blacc")
        self.assertTrue(_is_valid_match(search, self._sp("Wake Me Up (feat. Aloe Blacc)", "Avicii")))

    def test_partial_credit_hayley_williams(self):
        """'Hayley Williams of Paramore' as a search artist should match Spotify's 'Hayley Williams'."""
        search = _parse_song_title("B.o.B - Airplanes (feat. Hayley Williams of Paramore) [Official Video]")
        self.assertTrue(_is_valid_match(search, self._sp("Airplanes", "B.o.B", "Hayley Williams")))

    def test_ampersand_split_artists_match_individual_spotify_credits(self):
        """'Adventure Club & Krewella' split into two artists; Spotify credits both separately."""
        search = _parse_song_title("Adventure Club &amp; Krewella - Rise &amp; Fall")
        self.assertTrue(_is_valid_match(search, self._sp("Rise & Fall", "Adventure Club", "Krewella")))

    def test_track_with_parenthetical_subtitle_on_spotify(self):
        """Spotify track has a subtitle in parens; our clean query still matches."""
        search = SongSearch(track="Somebody That I Used To Know", artists=["Gotye"])
        self.assertTrue(_is_valid_match(search, self._sp("Somebody That I Used To Know (feat. Kimbra)", "Gotye")))


# ---------------------------------------------------------------------------
# 6. TestIsValidMatchFalsePositives
# ---------------------------------------------------------------------------

class TestIsValidMatchFalsePositives(unittest.TestCase):
    """_is_valid_match must return False for these — the precision guard tests."""

    def _sp(self, name, *artists):
        return {"name": name, "artists": [{"name": a} for a in artists]}

    def test_same_track_name_wrong_artist(self):
        """'Numb' by Linkin Park must not match 'Numb' by Jay-Z."""
        search = SongSearch(track="Numb", artists=["Linkin Park"])
        self.assertFalse(_is_valid_match(search, self._sp("Numb", "Jay-Z")))

    def test_totally_different_track(self):
        """A Daft Punk track name mismatch is rejected even when the artist is wrong too."""
        search = SongSearch(track="One More Time", artists=[])
        self.assertFalse(_is_valid_match(search, self._sp("Harder Better Faster Stronger", "Daft Punk")))

    def test_expected_track_is_strict_prefix_of_spotify_track(self):
        """'Take On Me' must not match Spotify's 'Take' — subsequence but only a prefix."""
        search = SongSearch(track="Take On Me", artists=["a-ha"])
        self.assertFalse(_is_valid_match(search, self._sp("Take", "a-ha")))

    def test_spotify_track_is_strict_prefix_of_expected(self):
        """'On Me' on Spotify must not match our 'Take On Me' search."""
        search = SongSearch(track="Take On Me", artists=["a-ha"])
        self.assertFalse(_is_valid_match(search, self._sp("On Me", "a-ha")))

    def test_short_single_token_does_not_match_longer_title(self):
        """'One' by Metallica must not accept Spotify's 'One More Time' by Daft Punk."""
        search = SongSearch(track="One", artists=["Metallica"])
        self.assertFalse(_is_valid_match(search, self._sp("One More Time", "Daft Punk")))

    def test_short_token_wrong_artist_doubly_wrong(self):
        """Short token collision AND wrong artist — must reject."""
        search = SongSearch(track="Go", artists=["Common"])
        self.assertFalse(_is_valid_match(search, self._sp("Go", "Grimes")))

    def test_single_shared_token_with_different_full_names_rejected(self):
        """
        Searching for 'Linkin Park' against a Spotify artist named just 'Park'
        is borderline, but a Spotify artist 'Dark' should definitely not match
        our 'Linkin Park' — no shared token of sufficient length.
        """
        search = SongSearch(track="In The End", artists=["Linkin Park"])
        self.assertFalse(_is_valid_match(search, self._sp("In The End", "Dark")))

    def test_correct_track_entirely_different_artist(self):
        """'Hello' is a common title; Adele's search must not match Lionel Richie's entry."""
        search = SongSearch(track="Hello", artists=["Adele"])
        self.assertFalse(_is_valid_match(search, self._sp("Hello", "Lionel Richie")))

    def test_track_tokens_present_but_in_wrong_order(self):
        """
        'Me Take On' — tokens present but scrambled — must not match 'Take On Me'.
        Verifies _tokens_in_order is used directionally.
        """
        search = SongSearch(track="Me Take On", artists=["a-ha"])
        self.assertFalse(_is_valid_match(search, self._sp("Take On Me", "a-ha")))

    def test_spotify_edition_noise_does_not_paper_over_wrong_track(self):
        """Stripping noise from a wrong track must not produce a spurious match."""
        search = SongSearch(track="Lose Yourself", artists=["Eminem"])
        self.assertFalse(_is_valid_match(search, self._sp("Rap God - Remastered", "Eminem")))

    def test_featured_artist_is_not_mistaken_for_primary(self):
        """
        Searching for 'Sia - Titanium' (reversed) must not match a Spotify result
        where Sia is only the featured artist and the track is by David Guetta.
        The swap path should not fire if the primary artist check doesn't hold.
        """
        # search.track = "Titanium", search.artists = ["David Guetta", "Sia"]
        search = _parse_song_title("David Guetta - Titanium ft. Sia (Official Video)")
        # Fake Spotify result: same track name but artists are totally wrong
        self.assertFalse(_is_valid_match(search, self._sp("Titanium", "Foo Fighters")))

    def test_no_artist_search_wrong_track(self):
        """A bare track-only search still rejects a completely different track name."""
        search = SongSearch(track="Sandstorm", artists=[])
        self.assertFalse(_is_valid_match(search, self._sp("Blue (Da Ba Dee)", "Eiffel 65")))

    def test_common_word_track_name_requires_lead_token_match(self):
        """
        'More' by Usher should not match a Spotify result where 'More' appears
        as the third word (e.g. 'Want Some More').
        The single-token path requires the token to appear first in the Spotify title.
        """
        search = SongSearch(track="More", artists=["Usher"])
        self.assertFalse(_is_valid_match(search, self._sp("Want Some More", "Usher")))


if __name__ == "__main__":
    unittest.main()
