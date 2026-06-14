import asyncio
import html
import logging
import os
import re
import uuid
from dataclasses import dataclass
from urllib.parse import urlencode

from anyascii import anyascii
import googleapiclient.discovery
import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from rapidfuzz import fuzz
from starlette.middleware.sessions import SessionMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube2Spotify")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "change-me-in-production"),
)
templates = Jinja2Templates(directory="templates")

MIGRATION_CACHE = {}

BASE_URI = os.environ.get("BASE_URI", "http://127.0.0.1:8080")

DEVELOPER_KEY = os.environ.get("YOUTUBE_DEVELOPER_KEY", "")

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = BASE_URI + "/callback"

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
ME_URL = "https://api.spotify.com/v1/me"

SPOTIFY_SCOPE = (
    "user-read-private user-read-email "
    "playlist-modify-public playlist-modify-private"
)

SEARCH_CONCURRENCY = int(os.environ.get("SEARCH_CONCURRENCY", "10"))
PLAYLIST_BATCH_SIZE = 100


def _fetch_youtube_playlist_items(playlist_id: str) -> list:
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=DEVELOPER_KEY)
    items = []
    page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=page_token,
        )
        response = request.execute()
        items.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


_BRACKETS = re.compile(r"\[[^\]]*\]")
_FEATURE_PAREN = re.compile(
    r"\(([^)]*(?:ft\.?|feat\.?|featuring|cover|by)[^)]*)\)", re.I
)
_OTHER_PAREN = re.compile(r"\([^)]*\)")
_PIPE_TAIL = re.compile(r"\s*\|.*$")
_SEGMENT_SPLIT = re.compile(r"\s+[-–—−]+\s*|\s*[-–—−]+\s+")
_ARTIST_SPLIT = re.compile(r"\s*(?:&|\+|,)\s*|\s+x\s+|\s+vs\.?\s+", re.I)
_FEAT_SPLIT = re.compile(
    r"\s*\bfeaturing\b\s*|\s*\bfeat\.?\s*|\s*\bft\.?\s*|\s*\bcover(?:ed)?(?:\s+by)?\b\s*", re.I
)
_TRAILING_NOISE = re.compile(
    r"(?:\s+(?:official|music\s+video|video|audio|lyrics?|with\s+lyrics|visualizer|"
    r"teaser|trailer|preview|hd|hq|4k|1080p?|mv|m/?v|full|extended|mix|remaster(?:ed)?|"
    r"cover|topic|explicit|clean|eurovision(?:\s+song\s+contest)?|live|performance|karaoke|\d{4}|kpop|"
    r"demon\s+hunters|lyric\s+video|sped\s+up))+\s*$",
    re.I,
)
_GENRES = frozenset({
    "house", "deep house", "tech house", "electro house", "progressive house",
    "future house", "bass house", "dubstep", "drumstep", "electronic", "edm", "trap",
    "trance", "techno", "dnb", "drum and bass", "drum & bass", "ambient",
    "pop", "rock", "hip hop", "hip-hop", "rap", "metal", "jazz", "classical",
    "folk", "country", "r&b", "rnb", "soul", "indie", "lofi", "lo-fi",
    "phonk", "garage", "synthwave", "vaporwave", "hardstyle", "psytrance",
})
_QUOTE_PAIRS = {'"': '"', "'": "'", "“": "”", "‘": "’"}


def _clean_segment(segment: str) -> str:
    segment = segment.strip()

    if len(segment) >= 2 and segment[0] in _QUOTE_PAIRS and segment[-1] == _QUOTE_PAIRS[segment[0]]:
        segment = segment[1:-1]
        
    segment = re.sub(r'["\u201c][^"\u201d]*["\u201d]|[\u2018][^\u2019]*[\u2019]', ' ', segment)
    segment = _TRAILING_NOISE.sub("", segment)
    segment = re.sub(r"\s+", " ", segment).strip()
    return segment


def _clean_channel_title(channel_title: str | None) -> str:
    if not channel_title:
        return ""
    channel_title = html.unescape(channel_title)
    channel_title = re.sub(r"\s+-\s+topic$", "", channel_title, flags=re.I)
    channel_title = re.sub(r"\s+(?:official|music|channel|records|vevo)$", "", channel_title, flags=re.I)
    return channel_title.strip()


def _extract_artists(segment: str) -> list[str]:
    artists: list[str] = []
    for part in _FEAT_SPLIT.split(segment):
        for name in _ARTIST_SPLIT.split(part):
            name = name.strip()
            name_words = name.split()
            if len(name_words) > 1 and name_words[-1].lower() in _GENRES:
                name = " ".join(name_words[:-1])
            if name:
                artists.append(name)
    return artists


def _parse_track_segment(segment: str) -> tuple[str, list[str]]:
    parts = _FEAT_SPLIT.split(segment, maxsplit=1)
    track = parts[0].strip()
    featured = _extract_artists(parts[1]) if len(parts) > 1 and parts[1].strip() else []
    return track, featured


def _is_junk_segment(segment: str) -> bool:
    if not segment.strip() or len(segment) > 100:
        return True
    return False


def _is_genre_segment(segment: str) -> bool:
    return segment.lower() in _GENRES


@dataclass(frozen=True)
class SongSearch:
    track: str
    artists: list[str]

    def queries(self) -> list[str]:
        queries: list[str] = []
        if self.artists:
            queries.append(f"{self.track} {' '.join(self.artists)}")
            queries.append(f"{self.artists[0]} {self.track}")
            queries.append(f'artist:"{self.artists[0]}" track:"{self.track}"')
        else:
            queries.append(self.track)
        return queries


def _strip_brackets_and_parens(text: str) -> str:
    text = _BRACKETS.sub(" ", text)
    text = _FEATURE_PAREN.sub(lambda m: f" {m.group(1)} ", text)
    text = _OTHER_PAREN.sub(" ", text)
    return text


def _normalize(text: str) -> str:
    text = text.lower().replace("$", "s")
    text = text.replace("´", "'").replace("`", "'").replace("’", "'").replace("‘", "'")
    text = anyascii(text)
    text = re.sub(r"[^\w\s']", " ", text)
    return " ".join(text.split())


_SPOTIFY_TRACK_NOISE = re.compile(
    r"\s*[-–(]\s*(?:"
    r"\d{4}\s*(?:remaster(?:ed)?|version|mix|edit|release)"
    r"|remaster(?:ed)?(?:\s+\d{4})?"
    r"|radio\s+edit"
    r"|single\s+version"
    r"|album\s+version"
    r"|original\s+(?:mix|version)"
    r"|deluxe(?:\s+edition)?"
    r"|explicit"
    r"|clean"
    r")\s*\)?\s*$",
    re.I,
)


def _strip_spotify_noise(name: str) -> str:
    """Remove common Spotify suffixes from a track name."""
    return _SPOTIFY_TRACK_NOISE.sub("", name).strip()


def _tokens_in_order(needles: list[str], haystack: list[str]) -> bool:
    meaningful = [n for n in needles if len(n) >= 2]
    if not meaningful:
        return False
    idx = 0
    for token in haystack:
        if idx < len(meaningful) and token == meaningful[idx]:
            idx += 1
    return idx == len(meaningful)


def _track_matches(expected: str, spotify_name: str) -> bool:
    parts = re.split(r"\s+x\s+|\s+vs\.?\s+|\s*/\s+", expected, flags=re.I)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        exp_norm = _normalize(part)
        got_norm = _normalize(spotify_name)

        if exp_norm == got_norm:
            return True

        exp_stripped = _normalize(_strip_spotify_noise(part))
        got_stripped = _normalize(_strip_spotify_noise(spotify_name))
        if exp_stripped and exp_stripped == got_stripped:
            return True

        exp_tokens = exp_norm.split()
        got_tokens = got_norm.split()
        if not exp_tokens:
            continue

        if len(exp_tokens) > 1 and _tokens_in_order(exp_tokens, got_tokens):
            return True

        if len(exp_tokens) == 1:
            token = exp_tokens[0]
            if token in got_tokens and got_tokens[0] == token:
                return True

        if len(exp_stripped) > 4:
            if fuzz.ratio(exp_stripped, got_stripped) > 80:
                return True
                
    return False


def _artist_matches(expected: str, spotify_artists: list[str]) -> bool:
    """
    Return True when `expected` artist name matches any name in `spotify_artists`.
    """
    exp_norm = _normalize(expected)
    exp_tokens = exp_norm.split()
    for name in spotify_artists:
        norm = _normalize(name)

        if norm == exp_norm:
            return True

        sp_tokens = norm.split()
        if len(exp_tokens) > 1 and _tokens_in_order(exp_tokens, sp_tokens):
            return True

        if len(sp_tokens) > 1 and _tokens_in_order(sp_tokens, exp_tokens):
            return True

        if fuzz.token_sort_ratio(exp_norm, norm) > 80:
            return True

    return False


def _artists_match(expected: list[str], spotify_artists: list[str]) -> bool:
    """
    Return True when at least one expected artist matches the Spotify result.
    """
    if any(_artist_matches(artist, spotify_artists) for artist in expected):
        return True

    expected_combined = " ".join(_normalize(artist) for artist in expected)
    spotify_combined = " ".join(_normalize(name) for name in spotify_artists)
    
    if fuzz.token_sort_ratio(expected_combined, spotify_combined) > 75:
        return True

    return False


def _is_valid_match(search: SongSearch, spotify_track: dict) -> bool:
    """
    Validate whether a Spotify search result is the right song for `search`.
    """
    spotify_name = spotify_track["name"]
    spotify_artists = [a["name"] for a in spotify_track["artists"]]

    if _track_matches(search.track, spotify_name):
        if search.artists and not _artists_match(search.artists, spotify_artists):
            # Track title matches but wrong artist: reject.
            return False
        return True

    if search.artists:
        for candidate_track in search.artists:
            if _track_matches(candidate_track, spotify_name):
                other_artists = [search.track] + [a for a in search.artists if a != candidate_track]
                if _artists_match(other_artists, spotify_artists):
                    return True

    if _track_matches(search.track, spotify_name):
        exp_combined = set(_normalize(search.track).split())
        for artist in search.artists:
            exp_combined.update(_normalize(artist).split())
            
        sp_combined = set(_normalize(spotify_name).split())
        for artist in spotify_artists:
            sp_combined.update(_normalize(artist).split())

        exp_meaningful = {t for t in exp_combined if len(t) >= 2}
        sp_meaningful = {t for t in sp_combined if len(t) >= 2}

        if exp_meaningful and sp_meaningful:
            if sp_meaningful.issubset(exp_meaningful) or exp_meaningful.issubset(sp_meaningful):
                if len(sp_meaningful.intersection(exp_meaningful)) >= 2:
                    return True

    return False


def _parse_song_title(title: str) -> SongSearch | None:
    if not title or title.strip().lower() in {"private video", "deleted video"}:
        return None
    title = html.unescape(title)
    title = _PIPE_TAIL.sub("", title)

    cleaned = _strip_brackets_and_parens(title)
    segments = [_clean_segment(s) for s in _SEGMENT_SPLIT.split(cleaned)]
    segments = [s for s in segments if s and not _is_junk_segment(s)]

    while segments and _is_genre_segment(segments[0]):
        segments.pop(0)

    if not segments:
        return None
    
    if len(segments) == 1:
        # Artist "Track"
        if m := re.search(r"^(.*?)\s+(['\"].*)$", segments[0]):
            artist_segment = m.group(1)
            track_segment = m.group(2)
        # : ~ // ,
        elif m := re.search(r"^(.*?)\s*(?::|~|//|,)\s*(.*)$", segments[0]):
            artist_segment = m.group(1)
            track_segment = m.group(2)
        # Track by Artist
        elif m := re.search(r"^(.*)\s+by\s+(.*)$", segments[0], re.I):
            track_segment = m.group(1)
            artist_segment = m.group(2)
        else:
            track, featured = _parse_track_segment(segments[0])
            return SongSearch(track=track, artists=featured)

        artist_segment = _clean_segment(artist_segment)
        track_segment = _clean_segment(track_segment)
    else:
        artist_segment = segments[0]
        track_segment = segments[1]

    artists = _extract_artists(artist_segment)
    track, featured = _parse_track_segment(track_segment)
    artists.extend(featured)
    return SongSearch(track=track, artists=artists)


async def _find_track_uri(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    video_title: str,
    video_channel_title: str | None,
    semaphore: asyncio.Semaphore,
) -> str | None:
    song_search = _parse_song_title(video_title)
    if not song_search:
        return None

    # Fallback to cleaned channel title if no artist was parsed from the video title
    if not song_search.artists and video_channel_title:
        cleaned_channel = _clean_channel_title(video_channel_title)
        if cleaned_channel:
            song_search = SongSearch(track=song_search.track, artists=[cleaned_channel])

    async with semaphore:
        for song_query in song_search.queries():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    search_res = await client.get(
                        "https://api.spotify.com/v1/search",
                        params={"q": song_query, "limit": "10", "type": "track"},
                        headers=headers,
                    )
                    
                    if search_res.status_code == 200:
                        for item in search_res.json().get("tracks", {}).get("items", []):
                            if _is_valid_match(song_search, item):
                                return item["uri"]
                        break
                    
                    elif search_res.status_code == 429:
                        retry_after = int(search_res.headers.get("Retry-After", 2))
                        logger.warning(
                            "Spotify API rate limit hit for query %r. Waiting %d seconds (attempt %d/%d)...",
                            song_query, retry_after, attempt + 1, max_retries
                        )
                        await asyncio.sleep(retry_after)
                    
                    else:
                        logger.error("Spotify search returned status code %d", search_res.status_code)
                        break
                        
                except httpx.HTTPError as e:
                    logger.warning("Network issue during track search: %s. Retrying...", e)
                    await asyncio.sleep(1)

    logger.info("No confident match for %r", video_title)
    return None


async def _add_tracks_to_playlist(
    client: httpx.AsyncClient,
    playlist_id: str,
    track_uris: list[str],
    headers: dict[str, str],
) -> None:
    for i in range(0, len(track_uris), PLAYLIST_BATCH_SIZE):
        chunk = track_uris[i : i + PLAYLIST_BATCH_SIZE]
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                res = await client.post(
                    f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                    json={"uris": chunk},
                    headers=headers,
                )
                
                if res.status_code in (200, 201):
                    break
                
                elif res.status_code == 429:
                    retry_after = int(res.headers.get("Retry-After", 2))
                    logger.warning(
                        "Rate limited adding tracks to playlist. Waiting %d seconds (attempt %d/%d)...",
                        retry_after, attempt + 1, max_retries
                    )
                    await asyncio.sleep(retry_after)
                
                else:
                    logger.error("Failed to add tracks chunk with status %d: %s", res.status_code, res.text)
                    break
                    
            except httpx.HTTPError as e:
                logger.warning("Network error while adding tracks: %s. Retrying...", e)
                await asyncio.sleep(1)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, error: str | None = None):
    errors = {}
    if error == "auth_denied":
        errors["auth"] = "Spotify connection was cancelled. Please authorise the app."
    elif error == "missing_code":
        errors["auth"] = "Failed to retrieve authorisation code from Spotify. Please try again."

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "errors": errors,
            "youtube_playlist": "",
            "spotify_playlist_name": "",
        },
    )


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("favicon.ico")


@app.post("/", response_class=HTMLResponse)
async def submit(
    request: Request,
    youtube_playlist: str = Form(...),
    spotify_playlist_name: str = Form(...),
):
    errors = {}
    if not youtube_playlist.strip():
        errors["youtube_playlist"] = "YouTube playlist URL is required."
    if not spotify_playlist_name.strip():
        errors["spotify_playlist_name"] = "Spotify playlist name is required."

    if errors:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "errors": errors,
                "youtube_playlist": youtube_playlist,
                "spotify_playlist_name": spotify_playlist_name,
            },
            status_code=400,
        )

    request.session["youtube_playlist"] = youtube_playlist.strip()
    request.session["spotify_playlist_name"] = spotify_playlist_name.strip()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login")
async def login(request: Request):
    if request.session.get("tokens"):
        return RedirectResponse(url="/processing", status_code=303)

    payload = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPE,
        "show_dialog": True,
    }
    return RedirectResponse(f"{AUTH_URL}/?{urlencode(payload)}")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/callback")
async def callback(request: Request, code: str | None = None, error: str | None = None):
    if error:
        if error == "access_denied":
            return RedirectResponse(url="/?error=auth_denied", status_code=303)
        raise HTTPException(status_code=400, detail=error)
    if not code:
        return RedirectResponse(url="/?error=missing_code", status_code=303)

    async with httpx.AsyncClient() as client:
        res = await client.post(
            TOKEN_URL,
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
            },
        )

    res_data = res.json()
    if res_data.get("error") or res.status_code != 200:
        logger.error(
            "Failed to receive token: %s",
            res_data.get("error", "No error information received."),
        )
        raise HTTPException(status_code=res.status_code)

    request.session["tokens"] = {
        "access_token": res_data.get("access_token"),
        "refresh_token": res_data.get("refresh_token"),
    }
    return RedirectResponse(url="/processing", status_code=303)


async def _refresh_session_tokens(request: Request) -> str | None:
    """Refreshes Spotify tokens using session data and returns the new access token."""
    tokens = request.session.get("tokens")
    if not tokens or not tokens.get("refresh_token"):
        return None

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                TOKEN_URL,
                auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": tokens["refresh_token"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if res.status_code == 200:
                res_data = res.json()
                new_token = res_data.get("access_token")
                if new_token:
                    # Update session data in place
                    tokens["access_token"] = new_token
                    request.session["tokens"] = tokens
                    return new_token
        except httpx.HTTPError as e:
            logger.error("Failed to refresh token: %s", e)

    return None


@app.get("/refresh")
async def refresh(request: Request):
    new_token = await _refresh_session_tokens(request)
    if not new_token:
        raise HTTPException(status_code=400, detail="Failed to refresh token or missing token in session.")
    return request.session["tokens"]


@app.get("/processing", response_class=HTMLResponse)
async def processing(request: Request):
    youtube_playlist = request.session.get("youtube_playlist")
    spotify_playlist_name = request.session.get("spotify_playlist_name")
    if not youtube_playlist or not spotify_playlist_name:
        return RedirectResponse(url="/", status_code=303)
        
    return templates.TemplateResponse("processing.html", {"request": request})


@app.get("/start-migration")
async def start_migration(request: Request):
    """Triggered asynchronously by JavaScript on the processing page."""
    youtube_playlist = request.session.get("youtube_playlist")
    spotify_playlist_name = request.session.get("spotify_playlist_name")
    if not youtube_playlist or not spotify_playlist_name:
        raise HTTPException(status_code=400, detail="No playlist information configured.")

    playlist_match = re.findall(r"list=([^&]+)", youtube_playlist)
    if not playlist_match:
        raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL.")

    playlist_id = playlist_match[0]
    
    try:
        videos = await asyncio.to_thread(_fetch_youtube_playlist_items, playlist_id)
    except Exception as e:
        logger.error("Failed to fetch YouTube playlist items: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch YouTube playlist items.")

    tokens = request.session.get("tokens")
    if not tokens:
        raise HTTPException(status_code=401, detail="Authentication token is missing.")

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    limits = httpx.Limits(
        max_connections=SEARCH_CONCURRENCY + 5,
        max_keepalive_connections=SEARCH_CONCURRENCY,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        profile_res = await client.get(ME_URL, headers=headers)
            
        # If the token is expired, refresh it inline once
        if profile_res.status_code == 401:
            new_token = await _refresh_session_tokens(request)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                profile_res = await client.get(ME_URL, headers=headers)

        profile_data = profile_res.json()
        if profile_res.status_code != 200:
            logger.error("Failed to get profile info: %s", profile_data)
            raise HTTPException(status_code=profile_res.status_code, detail="Failed to retrieve Spotify profile info.")

        playlist_res = await client.post(
            f"https://api.spotify.com/v1/users/{profile_data['id']}/playlists",
            json={"name": spotify_playlist_name, "public": False},
            headers=headers,
        )
        playlist_data = playlist_res.json()
        new_playlist_id = playlist_data["id"]

        semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)
        track_uris = await asyncio.gather(
            *[
                _find_track_uri(
                    client,
                    headers,
                    video["snippet"]["title"],
                    video["snippet"].get("videoOwnerChannelTitle"),
                    semaphore
                )
                for video in videos
            ]
        )
        unmatched_titles = [
            video["snippet"]["title"]
            for video, uri in zip(videos, track_uris)
            if not uri
        ]
        matched_uris = [uri for uri in track_uris if uri]
        if matched_uris:
            await _add_tracks_to_playlist(
                client, new_playlist_id, matched_uris, headers
            )

    ticket = str(uuid.uuid4())
    
    MIGRATION_CACHE[ticket] = {
        "profile_data": profile_data,
        "playlist_data": playlist_data,
        "matched_count": len(matched_uris),
        "total_count": len(track_uris),
        "unmatched_titles": unmatched_titles,
    }
    
    # Evict oldest records if cache gets too large
    if len(MIGRATION_CACHE) > 10:
        oldest_key = next(iter(MIGRATION_CACHE))
        MIGRATION_CACHE.pop(oldest_key, None)

    request.session["migration_ticket"] = ticket
    return {"status": "success"}


@app.get("/done", response_class=HTMLResponse)
async def done(request: Request):
    ticket = request.session.get("migration_ticket")
    if not ticket:
        return RedirectResponse(url="/", status_code=303)

    results = MIGRATION_CACHE.get(ticket)
    if not results:
        return RedirectResponse(url="/", status_code=303)

    request.session.pop("migration_ticket", None)

    return templates.TemplateResponse(
        "done.html",
        {
            "request": request,
            "data": results["profile_data"],
            "playlist": results["playlist_data"],
            "matched_count": results["matched_count"],
            "total_count": results["total_count"],
            "unmatched_titles": results["unmatched_titles"],
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("youtube2spotify:app", host="0.0.0.0", port=8080)