# YouTube2Spotify

Transfer songs from a public YouTube playlist to a new Spotify playlist. Enter a playlist URL, log in with Spotify, and the app matches each video title to a Spotify track.

## Setup

**YouTube** — [Google Cloud Console](https://console.cloud.google.com/): enable YouTube Data API v3, create an API key.

**Spotify** — [Developer Dashboard](https://developer.spotify.com/dashboard): create an app, copy Client ID and Secret, add a redirect URI matching `{BASE_URI}/callback`. Spotify does not allow `localhost`; use `127.0.0.1` for local dev and HTTPS in production.

## Environment variables

| Variable | Description |
|---|---|
| `YOUTUBE_DEVELOPER_KEY` | YouTube API key |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret |
| `BASE_URI` | App URL (default: `http://127.0.0.1:8080`) |
| `SECRET_KEY` | Session key (set in production) |

Redirect URI in Spotify must match `{BASE_URI}/callback`.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export YOUTUBE_DEVELOPER_KEY="..."
export SPOTIFY_CLIENT_ID="..."
export SPOTIFY_CLIENT_SECRET="..."

uvicorn youtube2spotify:app --reload --port 8080
```

Open **http://127.0.0.1:8080**.

## Run with Docker

```bash
docker build -t youtube2spotify .
docker run -p 8080:8080 \
  -e YOUTUBE_DEVELOPER_KEY="..." \
  -e SPOTIFY_CLIENT_ID="..." \
  -e SPOTIFY_CLIENT_SECRET="..." \
  -e BASE_URI="http://127.0.0.1:8080" \
  youtube2spotify
```
