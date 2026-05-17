"""
Instagram poster — Official Instagram Content Publishing API.

Flow per post:
  1. Upload JPEG to imgbb (public URL, free)
  2. Create Instagram media container via Graph API
  3. Poll until container status == FINISHED
  4. Publish container -> post is live

Token management:
  - Short-lived token (from .env) is exchanged for a 60-day long-lived token on first run
  - Long-lived token is saved to ig_token.json
  - Auto-refreshed when < 7 days remain
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from config import (
    IG_USER_ID, IG_ACCESS_TOKEN, IG_APP_SECRET,
    IMGBB_API_KEY, INSTAGRAM_USERNAME,
)

GRAPH      = "https://graph.instagram.com/v21.0"
TOKEN_FILE = Path("ig_token.json")


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _exchange_token(short_token: str) -> dict:
    """Exchange a short-lived token for a long-lived one (valid ~60 days)."""
    r = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type":    "ig_exchange_token",
            "client_secret": IG_APP_SECRET,
            "access_token":  short_token,
        },
        timeout=15,
    )
    if not r.ok:
        raise RuntimeError(
            f"Token exchange failed ({r.status_code}): {r.json()}\n"
            "-> Generate a fresh token on the Meta Developer portal and update IG_ACCESS_TOKEN in .env"
        )
    r.raise_for_status()
    data = r.json()
    expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
    return {"access_token": data["access_token"], "expires_at": expires_at.isoformat()}


def _refresh_token(token: str) -> dict:
    """Refresh a long-lived token for another 60 days."""
    r = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
    return {"access_token": data["access_token"], "expires_at": expires_at.isoformat()}


def _get_token() -> str:
    """Return a valid access token, refreshing when < 7 days remain."""
    if TOKEN_FILE.exists():
        stored     = json.loads(TOKEN_FILE.read_text())
        token      = stored["access_token"]
        expires_at = datetime.fromisoformat(stored["expires_at"])
        days_left  = (expires_at - datetime.now()).days

        if days_left > 7:
            return token
        if days_left >= 0:
            print(f"[instagram] Token expires in {days_left}d — refreshing...")
            try:
                stored = _refresh_token(token)
                TOKEN_FILE.write_text(json.dumps(stored, indent=2))
                return stored["access_token"]
            except Exception as e:
                print(f"[instagram] Refresh failed ({e}) — using existing token")
                return token
        print("[instagram] Token may be expired — update IG_ACCESS_TOKEN in .env and re-run")

    # No saved token — use .env token directly and store with 60-day expiry
    print("[instagram] Saving token from .env (valid ~60 days)...")
    stored = {
        "access_token": IG_ACCESS_TOKEN,
        "expires_at":   (datetime.now() + timedelta(days=60)).isoformat(),
    }
    TOKEN_FILE.write_text(json.dumps(stored, indent=2))
    return IG_ACCESS_TOKEN


# ---------------------------------------------------------------------------
# Image hosting (imgbb — free, no server needed)
# ---------------------------------------------------------------------------

def _host_image(image_path: str) -> str:
    """Upload JPEG to imgbb and return a public URL."""
    key = IMGBB_API_KEY.strip()
    file_size = Path(image_path).stat().st_size
    print(f"  [imgbb] Uploading {image_path} ({file_size/1024:.0f} KB)...")
    with open(image_path, "rb") as f:
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": key},
            files={"image": ("image.jpg", f, "image/jpeg")},
            timeout=60,
        )
    if not r.ok:
        raise RuntimeError(f"imgbb upload failed ({r.status_code}): {r.text[:400]}")
    url = r.json()["data"]["url"]
    print(f"  [imgbb] Hosted: {url[:70]}...")
    return url


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

def post_image(image_path: str, caption: str) -> str:
    token = _get_token()

    # 1 — Host image publicly
    image_url = _host_image(image_path)

    # 2 — Create media container
    print(f"  [instagram] Posting as user_id={IG_USER_ID}")
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        params={
            "image_url":    image_url,
            "caption":      caption[:2200],
            "access_token": token,
        },
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Create container failed ({r.status_code}): {r.json()}")
    container_id = r.json()["id"]
    print(f"  [instagram] Container: {container_id}")

    # 3 — Poll until FINISHED (usually < 30 s)
    for attempt in range(20):
        time.sleep(4)
        status_data = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=10,
        ).json()
        status = status_data.get("status_code", "IN_PROGRESS")
        print(f"  [instagram] Status: {status} (attempt {attempt + 1})")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Container processing failed: {status_data}")
    else:
        raise RuntimeError("Container processing timed out after 80 s")

    # 4 — Publish
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    r.raise_for_status()
    post_id = r.json()["id"]
    url = f"https://www.instagram.com/{INSTAGRAM_USERNAME}/"
    print(f"[instagram] Live -> {url}")
    return url
