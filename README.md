<p align="center">
  <a href="https://trd-ferguson.github.io/Canadian-RSS/">
    <img src="Aggregated%20Feed/assets/RSS-maple-favicon.svg" alt="Canadian-RSS maple leaf RSS mark" width="112">
  </a>
</p>

<h1 align="center">Canadian-RSS</h1>

<p align="center">
<b>Canadian media scan & news feed wall</b> | A chronological RSS aggregator, reader, feed wall. 
  Accessibility by design | Compatible with leading assistive technology and w3 standard screen readers. 
</p>

<p align="center">
  <a href="https://trd-ferguson.github.io/Canadian-RSS/">Open the news reader</a>
  ·
  <a href="https://trd-ferguson.github.io/Canadian-RSS/feed.xml">Subscribe to the RSS feed</a>
  ·
  <a href="https://github.com/Trd-Ferguson/Canadian-RSS">Browse the source</a>
</p>

---

## README

This template repository builds and hosts a GitHub Page in the main repository. 

The site is live at **[Canadian-RSS news reader](https://trd-ferguson.github.io/Canadian-RSS/)**. 

The re-parsed items items are presented newest first, with the publisher, publication date, summary, and a link to the original article. Select a headline or image to read the story at its source; use **Read more** to expand a longer summary.
    
If you prefer a dedicated feed reader, copy or open the feed URL in your RSS app:

**[https://trd-ferguson.github.io/Canadian-RSS/feed.xml](https://trd-ferguson.github.io/Canadian-RSS/feed.xml)**


## What’s in the feed

This template is a comprehensive, authoritative, Canadian public media RSS feed that combines configured publisher and public-service feeds into one RSS archive. Sources include Public Canadian newsrooms, a selection of [OpenGovernment RSS Feeds](https://open.canada.ca/en/rss-feeds), indigenous governments and National Indigenous Organizations (NIOs), other [Government of Canada feeds](https://www.canada.ca/en/news/subscribe-emails.html#:~:text=use-,RSS%20feeds), and fully-Canadian owned outlets. The current source list is maintained in [`feeds/feeds.json`](feeds/feeds.json).

xml format makes the feed and site highly accessible to many adaptive and assistive technology. This Ideal for  

Stories and RSS <items> remain the property of their respective publishers; follow the source link for the complete article and context.

## More Info | Beginner friendly
### How it works 

After building [Aggregated Feed/assets](Aggregated Feed/assets) and customizing the [index.html](Aggregated Feed/index.html) template, the [Aggregated Feed](/Aggregated Feed) is initialized and built by the aggregator.yml. After first run the Aggregated Feed requires the feed.xml, feed_status_log.json, keep_alive.txt to function and will continue to are build and deployed to the github-pages environment by the dual [.github/workflows/aggregator.yml](.github/workflows/aggregator.yml) cron job.

This GitHub Actions workflow currently runs the [aggregate.py](aggregate.py) on a two-hour schedule and can also be dispatched manually by selecting `Run workflow` in the **Actions** tab. It will fetch each configured feed, merge new stories into the existing archive, sort the output newest first, upload Pages Artifact and publish the reader and feed with GitHub Pages.

The archive avoids duplicating items with the same feed identifier and records recent per-source check results in `Aggregated Feed/feed_status_log.json`. If a publisher’s feed is unavailable or changes format, that source may not have fresh items until a later successful check; the other feeds can still update.

## DIY

### Project layout

```text
.
├── .github/workflows/       Scheduled aggregation and Pages deployment
├── Aggregated Feed/         Published reader, RSS archive, and status history
│   └── assets/              Feed favicon and other site assets
│   └── feed.xml             Aggregated feed and archive
│   └── index.html           Site HTML + CSS + JavaScript 
├── feeds/feeds.json         Source feeds and display configuration array
├── aggregate.py             Fetches, merges, and writes the RSS archive
└── LICENSE                  GNU Affero General Public License v3.0
```

- Browse the live reader: https://trd-ferguson.github.io/Canadian-RSS/
- Subscribe to the aggregated feed: https://trd-ferguson.github.io/Canadian-RSS/feed.xml
- View the source: https://github.com/Trd-Ferguson/Canadian-RSS


### Add or update a source

Edit `feeds/feeds.json`. Each source entry includes an `id`, display `name`, `feed_url`, `icon_url`, and `fallback_image_url`. The optional `card_pres_set` value controls special presentation for government-style cards. Keep each `id` unique: archived stories use it to retain their source attribution and match the reader’s feed configuration.

After changing a source, run the **RSS Aggregator** or **Feed Rebuild & Deploy** workflow from the Actions tab to refresh the archive and published site.


### Run the aggregator locally

A public repo built can be completed with any github account and chrome, safari, firefox, or MS edge. To run the build locally you will need Python 3.11 or later and access to the configured feeds. From the repository root:

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

## License

The project is licensed under the [GNU Affero General Public License v3.0](LICENSE). News articles, logos, and other publisher-provided material linked or referenced by the feed remain subject to their respective owners’ terms and rights.
