"""Copy the latest @tidesintimes posts from Behold into this site.

Writes data/instagram.json and img/ig/<id>.jpg, so the pages load the photos
from kayihan.net and browser blockers have no third-party request to stop.
If the feed is unavailable or empty, the existing files are left alone.
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

FEED_URL = "https://feeds.behold.so/uQB1qMwA7jNGVWDD8DhD"
MAX_POSTS = 6
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "instagram.json"
IMAGE_DIR = ROOT / "img" / "ig"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "kayihan.net-instagram-update"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(), response.headers.get("Content-Type", "")


def image_url(post):
    sizes = post.get("sizes") or {}
    medium = sizes.get("medium") or {}
    return medium.get("mediaUrl") or post.get("thumbnailUrl") or post.get("mediaUrl")


def post_id(post):
    value = str(post.get("id") or "")
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return hashlib.sha1(post["permalink"].encode("utf-8")).hexdigest()[:16]


def main():
    body, _ = fetch(FEED_URL)
    feed = json.loads(body.decode("utf-8"))
    entries = []
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for post in (feed.get("posts") or [])[:MAX_POSTS]:
        url = image_url(post)
        if not url or not post.get("permalink"):
            continue
        name = post_id(post) + ".jpg"
        path = IMAGE_DIR / name
        if not path.exists():
            data, content_type = fetch(url)
            if not content_type.startswith("image/") or not data:
                raise ValueError(f"Not an image: {url} ({content_type})")
            path.write_bytes(data)
        alt = post.get("altText") or post.get("prunedCaption") or post.get("caption") or ""
        entries.append({
            "permalink": post["permalink"],
            "alt": " ".join(alt.split())[:160],
            "image": f"img/ig/{name}",
        })

    if not entries:
        raise SystemExit("The feed returned no usable posts, so nothing was changed.")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps({"posts": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    keep = {Path(entry["image"]).name for entry in entries}
    for old in IMAGE_DIR.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()

    print(f"Saved {len(entries)} posts.")


if __name__ == "__main__":
    main()
