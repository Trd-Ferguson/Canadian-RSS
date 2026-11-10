import os
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import feedparser
import requests
from lxml import html

FEEDS_CONFIG_PATH = "feeds/feeds.json"
STATUS_LOG_PATH = "Aggregated Feed/feed_status_log.json"
OUTPUT_FEED_PATH = "Aggregated Feed/feed.xml"

if not os.path.exists(FEEDS_CONFIG_PATH):
    raise FileNotFoundError(f"Configuration profile layout missing at {FEEDS_CONFIG_PATH}")

with open(FEEDS_CONFIG_PATH, "r", encoding="utf-8") as f:
    FEED_CONFIGS = json.load(f)

status_logs = {}
if os.path.exists(STATUS_LOG_PATH):
    try:
        with open(STATUS_LOG_PATH, "r", encoding="utf-8") as f:
            status_logs = json.load(f)
    except Exception:
        status_logs = {}

existing_xml_items = {}
if os.path.exists(OUTPUT_FEED_PATH):
    try:
        tree = ET.parse(OUTPUT_FEED_PATH)
        for item in tree.findall(".//item"):
            guid_node = item.find("guid")
            if guid_node is not None and guid_node.text:
                existing_xml_items[guid_node.text] = item
                if "timestamp" not in item.attrib:
                    pub_date_str = item.find("pubDate").text
                    try:
                        dt = datetime.strptime(pub_date_str.strip(), "%a, %d %b %Y %H:%M:%S GMT")
                        item.set("timestamp", str(dt.timestamp()))
                    except Exception:
                        item.set("timestamp", str(datetime.utcnow().timestamp()))
    except Exception as e:
        print(f"Base data timeline file unreadable. Starting fresh. Error: {e}")

def clean_html_summary(html_text):
    if not html_text:
        return ""
    try:
        doc = html.fromstring(html_text)
        text = doc.text_content().strip()
        return text[:300] + "..." if len(text) > 300 else text
    except Exception:
        text = re.sub(r'<[^<]+?>', '', html_text)
        return text[:300] + "..." if len(text) > 300 else text

def extract_story_image(entry):
    if "media_content" in entry and entry["media_content"]:
        return entry["media_content"][0].get("url")
    if "links" in entry:
        for link in entry["links"]:
            if "image" in link.get("type", ""):
                return link.get("href")
    html_content = entry.get("description", "") + " " + entry.get("summary", "")
    if html_content:
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
        if imgs:
            return imgs[0]
    return None

def parse_entry_date(entry):
    for key in ["published_parsed", "updated_parsed", "created_parsed"]:
        if entry.get(key):
            try:
                return datetime(*entry[key][:6])
            except Exception:
                continue
    return datetime.utcnow()

for cfg in FEED_CONFIGS:
    feed_id = cfg["id"]
    feed_url = cfg["feed_url"]
    if feed_id not in status_logs or not isinstance(status_logs[feed_id], list):
        status_logs[feed_id] = []
    current_status = {
        "checked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "changed_at": "NONE",
        "error": "NONE",
    }
    try:
        response = requests.get(
            feed_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 RSS Aggregator Engine"},
        )
        if response.status_code != 200:
            raise Exception(f"HTTP Server responded with status code: {response.status_code}")
        parsed = feedparser.parse(response.content)
        if parsed.bozo:
            print(f"Non-fatal formatting warning on profile context {feed_id}")
        new_items_found = False
        for entry in parsed.entries:
            guid = entry.get("id") or entry.get("guid") or entry.get("link")
            if not guid:
                continue
            pub_date = parse_entry_date(entry)
            img_url = extract_story_image(entry) or cfg.get("fallback_image_url", "")
            summary = clean_html_summary(entry.get("summary") or entry.get("description", ""))
            title = entry.get("title", "Untitled Story").strip()
            author = entry.get("author") or entry.get("dc_creator") or "Staff Writer"
            if guid in existing_xml_items:
                old_item = existing_xml_items[guid]
                old_title = (old_item.find("title").text or "").strip()
                old_desc = (old_item.find("description").text or "").strip()
                edited_attrs = []
                if old_title != title and not old_title.startswith("EDITED"):
                    edited_attrs.append("title")
                if old_desc != summary and not old_desc.startswith("EDITED"):
                    edited_attrs.append("summary")
                if edited_attrs:
                    attr_labels = ", ".join(edited_attrs)
                    summary = f"EDITED [{attr_labels}] {summary}"
                    new_items_found = True
                else:
                    continue
            else:
                new_items_found = True
            item_element = ET.Element("item")
            ET.SubElement(item_element, "title").text = title
            ET.SubElement(item_element, "link").text = entry.get("link", "")
            ET.SubElement(item_element, "guid", isPermaLink="false").text = guid
            ET.SubElement(item_element, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            ET.SubElement(item_element, "author").text = author
            ET.SubElement(item_element, "source_name").text = cfg["name"]
            ET.SubElement(item_element, "source_icon").text = cfg.get("icon_url", "")
            ET.SubElement(item_element, "story_image").text = img_url
            ET.SubElement(item_element, "description").text = summary
            item_element.set("timestamp", str(pub_date.timestamp()))
            existing_xml_items[guid] = item_element
        if new_items_found:
            current_status["changed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception as e:
        current_status["error"] = str(e)
        print(f"Exception encountered parsing endpoint layer {feed_id}: {e}")
    status_logs[feed_id].insert(0, current_status)
    status_logs[feed_id] = status_logs[feed_id][:5]

def get_item_timestamp(node):
    try:
        return float(node.get("timestamp", 0))
    except (TypeError, ValueError):
        return 0.0

sorted_xml_nodes = sorted(existing_xml_items.values(), key=get_item_timestamp, reverse=True)
rss_root = ET.Element("rss", {"version": "2.0", "xmlns:atom": "http://w3.org"})
channel = ET.SubElement(rss_root, "channel")
ET.SubElement(channel, "title").text = "Unified Canadian News Feed"
ET.SubElement(channel, "link").text = "https://github.com"
ET.SubElement(channel, "description").text = "Chronological aggregated Canadian timeline feed wall."
ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

for item in sorted_xml_nodes:
    export_item = ET.Element("item")
    for child in item:
        ET.SubElement(export_item, child.tag).text = child.text

    if "timestamp" in item.attrib:
        export_item.set("timestamp", item.attrib["timestamp"])
    channel.append(export_item)

ET.ElementTree(rss_root).write(OUTPUT_FEED_PATH, encoding="utf-8", xml_declaration=True)

with open(STATUS_LOG_PATH, "w", encoding="utf-8") as f:
    json.dump(status_logs, f, indent=2)

print(f"Compilation finished. Sync target index database currently tracks {len(sorted_xml_nodes)} sorted lifecycle entries.")

# License: GNU General Public License v3.0 (GNU AFFERO GENERAL PUBLIC LICENSE)
