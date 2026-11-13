import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime

import feedparser
import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FEEDS_CONFIG_PATH = "feeds/feeds.json"
STATUS_LOG_PATH = "Aggregated Feed/feed_status_log.json"
OUTPUT_FEED_PATH = "Aggregated Feed/feed.xml"

SITE_URL = "https://trd-ferguson.github.io/Canadian-RSS/"
SELF_FEED_URL = SITE_URL + "feed.xml"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", ATOM)

# Optional one-time helpers for old archived items whose feed was renamed or dropped:
LEGACY_NAMES = {}   # e.g. {"Old Feed Name": "the_maple"}  (old source_name -> feed id)
OLD_FALLBACKS = set()  # e.g. {"https://old.example.com/img.png"}  (previous fallback_image_url values)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TEXT_FIELDS = ["title", "link", "author", "source_id", "source_name",
               "source_icon", "story_image", "description"]
EDIT_PREFIX = re.compile(r"^EDITED \[[^\]]*\] ")
BAD_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


# ---------- helpers ----------
def utcnow():
    return datetime.now(timezone.utc)


def clean(text):
    return BAD_XML_CHARS.sub("", text or "").strip()


def summarize(raw):
    if not raw:
        return ""
    try:
        text = html.fromstring(raw).text_content()
    except Exception:
        text = re.sub(r"<[^<]+?>", "", raw)
    text = clean(text)
    return text[:300] + "..." if len(text) > 300 else text


def extract_story_image(entry):
    media = entry.get("media_content")
    if media and media[0].get("url"):
        return media[0]["url"]
    for link in entry.get("links", []):
        if "image" in link.get("type", ""):
            return link.get("href")
    blob = (entry.get("description") or "") + " " + (entry.get("summary") or "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', blob)
    return match.group(1) if match else None


def entry_timestamp(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        if entry.get(key):
            try:
                return datetime(*entry[key][:6], tzinfo=timezone.utc).timestamp()
            except Exception:
                continue
    return utcnow().timestamp()


def make_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = USER_AGENT
    return session


# ---------- load state ----------
if not os.path.exists(FEEDS_CONFIG_PATH):
    raise FileNotFoundError(f"Missing feed config: {FEEDS_CONFIG_PATH}")
with open(FEEDS_CONFIG_PATH, "r", encoding="utf-8") as f:
    FEED_CONFIGS = json.load(f)
BY_ID = {c["id"]: c for c in FEED_CONFIGS}
BY_NAME = {c["name"]: c for c in FEED_CONFIGS}

status_logs = {}
if os.path.exists(STATUS_LOG_PATH):
    try:
        with open(STATUS_LOG_PATH, "r", encoding="utf-8") as f:
            status_logs = json.load(f)
    except Exception:
        status_logs = {}


def load_archive():
    """Read every item from the existing feed.xml. Blank/rootless files start a fresh archive;
    a file with real content that fails to parse aborts so the archive is never wiped."""
    archive = {}
    if not os.path.exists(OUTPUT_FEED_PATH):
        return archive
    with open(OUTPUT_FEED_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    if "<rss" not in raw and "<item" not in raw:
        print("feed.xml has no feed content; starting a fresh archive.")
        return archive
    root = ET.fromstring(raw.encode("utf-8"))
    for el in root.iter("item"):
        guid = el.findtext("guid")
        if not guid:
            continue
        rec = {field: el.findtext(field) or "" for field in TEXT_FIELDS}
        img = el.find("story_image")
        rec["fallback"] = img is not None and img.get("fallback") == "1"
        try:
            dt = parsedate_to_datetime(el.findtext("pubDate"))
            rec["ts"] = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()
        except Exception:
            rec["ts"] = utcnow().timestamp()
        archive[guid] = rec
    return archive


archive = load_archive()
session = make_session()

# ---------- fetch & merge ----------
for cfg in FEED_CONFIGS:
    feed_id = cfg["id"]
    if not isinstance(status_logs.get(feed_id), list):
        status_logs[feed_id] = []
    status = {"checked_at": utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
              "changed_at": "NONE", "error": "NONE"}
    try:
        response = session.get(cfg["feed_url"], timeout=(10, 30))
        if response.status_code != 200:
            raise Exception(f"HTTP Server responded with status code: {response.status_code}")
        parsed = feedparser.parse(response.content)
        changed = False

        for entry in parsed.entries:
            guid = entry.get("id") or entry.get("guid") or entry.get("link")
            if not guid:
                continue
            title = clean(entry.get("title")) or "Untitled Story"
            summary = summarize(entry.get("summary") or entry.get("description"))
            real_img = extract_story_image(entry)
            rec = archive.get(guid)

            if rec is None:
                archive[guid] = {
                    "title": title,
                    "link": entry.get("link", ""),
                    "author": clean(entry.get("author") or entry.get("dc_creator")) or " ",
                    "source_id": feed_id,
                    "source_name": cfg["name"],
                    "source_icon": cfg.get("icon_url", ""),
                    "story_image": real_img or "",
                    "fallback": not real_img,
                    "description": summary,
                    "ts": entry_timestamp(entry),
                }
                changed = True
                continue

            # Legacy item with no source_id: it's in this feed, so we now know its source
            if not rec["source_id"]:
                rec["source_id"] = feed_id
                if not real_img:
                    rec["fallback"] = True  # nothing real in the feed, so the stored image is an old fallback

            # Existing item: flag edits, and upgrade a fallback image if a real one appears
            edited = [name for name, old, new in (
                ("title", rec["title"], title),
                ("summary", EDIT_PREFIX.sub("", rec["description"]), summary),
            ) if old != new]
            if edited:
                rec["title"] = title
                rec["description"] = f"EDITED [{', '.join(edited)}] {summary}"
                changed = True
            if real_img and real_img != rec["story_image"]:
                rec["story_image"], rec["fallback"] = real_img, False

        if changed:
            status["changed_at"] = utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception as e:
        status["error"] = str(e)
        print(f"Error on {feed_id}: {e}")

    status_logs[feed_id].insert(0, status)
    status_logs[feed_id] = status_logs[feed_id][:5]

# ---------- sync source metadata across the WHOLE archive ----------
for rec in archive.values():
    cfg = (BY_ID.get(rec["source_id"])
           or BY_NAME.get(rec["source_name"])
           or BY_ID.get(LEGACY_NAMES.get(rec["source_name"])))
    if not cfg:
        continue  # source unknown: leave the archived item untouched
    fallback_img = cfg.get("fallback_image_url", "")
    rec["source_id"] = cfg["id"]
    rec["source_name"] = cfg["name"]
    rec["source_icon"] = cfg.get("icon_url", "")
    if rec["fallback"] or not rec["story_image"] or rec["story_image"] in (fallback_img, *OLD_FALLBACKS):
        rec["story_image"], rec["fallback"] = fallback_img, True

# ---------- write feed.xml (newest first) ----------
rss = ET.Element("rss", {"version": "2.0"})
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "Unified Canadian News Feed"
ET.SubElement(channel, "link").text = SITE_URL
ET.SubElement(channel, "description").text = "Chronological aggregated Canadian feed wall."
ET.SubElement(channel, "language").text = "en-ca"
ET.SubElement(channel, "lastBuildDate").text = format_datetime(utcnow(), usegmt=True)
ET.SubElement(channel, f"{{{ATOM}}}link",
              {"href": SELF_FEED_URL, "rel": "self", "type": "application/rss+xml"})

for guid, rec in sorted(archive.items(), key=lambda kv: kv[1]["ts"], reverse=True):
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = rec["title"]
    ET.SubElement(item, "link").text = rec["link"]
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
    ET.SubElement(item, "pubDate").text = format_datetime(
        datetime.fromtimestamp(rec["ts"], timezone.utc), usegmt=True)
    ET.SubElement(item, "author").text = rec["author"]
    ET.SubElement(item, "source_id").text = rec["source_id"]
    ET.SubElement(item, "source_name").text = rec["source_name"]
    ET.SubElement(item, "source_icon").text = rec["source_icon"]
    ET.SubElement(item, "story_image", {"fallback": "1"} if rec["fallback"] else {}).text = rec["story_image"]
    ET.SubElement(item, "description").text = rec["description"]

ET.indent(rss, space="  ")
tmp_path = OUTPUT_FEED_PATH + ".tmp"
ET.ElementTree(rss).write(tmp_path, encoding="utf-8", xml_declaration=True)
os.replace(tmp_path, OUTPUT_FEED_PATH)

with open(STATUS_LOG_PATH, "w", encoding="utf-8") as f:
    json.dump(status_logs, f, indent=2)

print(f"Done. Archive holds {len(archive)} items.")
