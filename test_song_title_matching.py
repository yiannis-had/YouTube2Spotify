import unittest

from youtube2spotify import SongSearch, _is_valid_match, _parse_song_title


class SongTitleParsingTests(unittest.TestCase):
    def test_parse_song_title_across_genres_and_eras(self):
        cases = [
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
            ("Daft Punk - One More Time", "One More Time", ["Daft Punk"]),
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

        for title, expected_track, expected_artists in cases:
            with self.subTest(title=title):
                parsed = _parse_song_title(title)
                self.assertIsNotNone(parsed)
                self.assertEqual(expected_track, parsed.track)
                self.assertEqual(expected_artists, parsed.artists)

    def test_parse_song_title_discards_non_song_entries(self):
        self.assertIsNone(_parse_song_title(""))
        self.assertIsNone(_parse_song_title("   "))
        self.assertIsNone(_parse_song_title("Private video"))


class SongMatchValidationTests(unittest.TestCase):
    def test_valid_match_accepts_direct_and_swapped_patterns(self):
        cases = [
            (
                _parse_song_title("Queen - Bohemian Rhapsody"),
                {"name": "Bohemian Rhapsody - Remastered 2011", "artists": [{"name": "Queen"}]},
                True,
            ),
            (
                _parse_song_title("Miles Davis - So What"),
                {"name": "So What", "artists": [{"name": "Miles Davis"}]},
                True,
            ),
            (
                _parse_song_title("BTS - Dynamite"),
                {"name": "Dynamite", "artists": [{"name": "BTS"}]},
                True,
            ),
            (
                _parse_song_title("Take On Me - a-ha"),
                {"name": "Take On Me", "artists": [{"name": "a-ha"}]},
                True,
            ),
            (
                SongSearch(track="Bad Guy", artists=["Billie Eilish"]),
                {"name": "bad guy", "artists": [{"name": "Billie Eilish"}]},
                True,
            ),
            (
                SongSearch(track="Numb", artists=["Linkin Park"]),
                {"name": "Numb", "artists": [{"name": "Jay-Z"}]},
                False,
            ),
            (
                SongSearch(track="One More Time", artists=[]),
                {"name": "One More Time (Radio Edit)", "artists": [{"name": "Daft Punk"}]},
                True,
            ),
            (
                SongSearch(track="One More Time", artists=[]),
                {"name": "Harder Better Faster Stronger", "artists": [{"name": "Daft Punk"}]},
                False,
            ),
            (
                SongSearch(track="Take On Me", artists=["a-ha"]),
                {"name": "On Me", "artists": [{"name": "a-ha"}]},
                False,
            ),
        ]

        for search, spotify_track, expected in cases:
            with self.subTest(search=search, spotify_track=spotify_track):
                self.assertIsNotNone(search)
                self.assertEqual(expected, _is_valid_match(search, spotify_track))


if __name__ == "__main__":
    unittest.main()
