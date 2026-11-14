<p align="center">
  <a href="https://trd-ferguson.github.io/Canadian-RSS/">
    <img src="Aggregated%20Feed/assets/RSS-maple-favicon.svg" alt="Canadian-RSS maple leaf RSS mark" width="112">
  </a>
</p>

<h1 align="center">Canadian-RSS</h1>

<p align="center">
  A chronological scan of Canadian news, public-interest reporting, and government updates — gathered from RSS and Atom feeds in one place.
</p>

<p align="center">
  <a href="https://trd-ferguson.github.io/Canadian-RSS/">Open the news reader</a>
  ·
  <a href="https://trd-ferguson.github.io/Canadian-RSS/feed.xml">Subscribe to the RSS feed</a>
  ·
  <a href="https://github.com/Trd-Ferguson/Canadian-RSS">Browse the source</a>
</p>

---

## Start reading

Visit the [Canadian-RSS news reader](https://trd-ferguson.github.io/Canadian-RSS/) to scan recent stories. Items are presented newest first, with the publisher, publication date, summary, and a link to the original article. Select a headline or image to read the story at its source; use **Read more** to expand a longer summary.

Prefer a dedicated feed reader? Copy or open this feed URL in your RSS app:

**[https://trd-ferguson.github.io/Canadian-RSS/feed.xml](https://trd-ferguson.github.io/Canadian-RSS/feed.xml)**

## What’s in the scan

Canadian-RSS combines configured publisher and public-service feeds into one RSS archive. Sources include Canadian newsrooms and independent outlets, Indigenous media and organizations, the Prime Minister’s Office, the Canada Gazette, and Government of Canada news. The current source list is maintained in [`feeds/feeds.json`](feeds/feeds.json).

The site is a reader and aggregator, not the publisher of the linked reporting. Stories remain the property of their respective publishers; follow the source link for the complete article and context.

## How updates work

A GitHub Actions workflow runs the Python aggregator on a two-hour schedule and can also be started manually from the repository’s **Actions** tab. It fetches each configured feed, merges new stories into the existing archive, sorts the output newest first, and publishes the reader and feed with GitHub Pages.

The archive avoids duplicating items with the same feed identifier and records recent per-source check results in `Aggregated Feed/feed_status_log.json`. If a publisher’s feed is unavailable or changes format, that source may not have fresh items until a later successful check; the other feeds can still update.

## For maintainers

### Add or update a source

Edit `feeds/feeds.json`. Each source entry includes an `id`, display `name`, `feed_url`, `icon_url`, and `fallback_image_url`. The optional `card_pres_set` value controls special presentation for government-style cards. Keep each `id` unique: archived stories use it to retain their source attribution and match the reader’s feed configuration.

After changing a source, run the **RSS Aggregator** or **Feed Rebuild & Deploy** workflow from the Actions tab to refresh the archive and published site.

### Run the aggregator locally

You need Python 3.11 or later and access to the configured feeds. From the repository root:

```bash
python -m pip install feedparser lxml requests
python aggregate.py
```

The script reads `feeds/feeds.json` and the existing archive, then writes `Aggregated Feed/feed.xml` and `Aggregated Feed/feed_status_log.json`. It makes network requests to the configured feed URLs; run it from the repository root so its relative file paths resolve correctly.

To preview the Pages site locally, put the source configuration where the reader expects it and serve the published directory over HTTP:

```bash
mkdir -p "Aggregated Feed/feeds"
cp feeds/feeds.json "Aggregated Feed/feeds/feeds.json"
python -m http.server 8000 --directory "Aggregated Feed"
```

Then open [http://localhost:8000](http://localhost:8000). Serving over HTTP is important because the reader fetches the feed and configuration as files.

## Project layout

```text
.
├── .github/workflows/       Scheduled aggregation and Pages deployment
├── Aggregated Feed/         Published reader, RSS archive, and status history
│   └── assets/              Maple RSS favicon and site assets
├── feeds/feeds.json         Source feed and display configuration
├── aggregate.py             Fetches, merges, and writes the RSS archive
└── LICENSE                  GNU Affero General Public License v3.0
```

## License

The project is licensed under the [GNU Affero General Public License v3.0](LICENSE). News articles, logos, and other publisher-provided material linked or referenced by the feed remain subject to their respective owners’ terms and rights.
