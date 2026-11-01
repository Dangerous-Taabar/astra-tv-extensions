# -*- coding: utf-8 -*-
"""
AnimeDubHindi Provider - Native Hindi Dubbed Anime Engine
Ported from Faisal0786/Desi Cloudstream Extension (AnimeDubHindi.cs3).
Zero external dependencies (uses FastHtml).
Target: https://www.animedubhindi.link & https://new.adhlinks.com
"""

import re
import json
import ssl
import urllib.parse
import urllib.request
from resources.lib.core.fast_html import FastHtml

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

DEFAULT_DOMAIN = "https://www.animedubhindi.link"
_DYNAMIC_DOMAIN_CACHE = None


def get_animedub_domain():
    """Fetches latest unblocked domain from Faisal0786's live domains map."""
    global _DYNAMIC_DOMAIN_CACHE
    if _DYNAMIC_DOMAIN_CACHE:
        return _DYNAMIC_DOMAIN_CACHE

    try:
        url = "https://raw.githubusercontent.com/Faisal0786/test/main/urls.json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
            domain = data.get("animedubhindi", DEFAULT_DOMAIN).rstrip("/")
            if domain.startswith("http"):
                if not domain.startswith("https://www.") and "animedubhindi" in domain:
                    domain = domain.replace("https://", "https://www.")
                _DYNAMIC_DOMAIN_CACHE = domain
                return _DYNAMIC_DOMAIN_CACHE
    except Exception:
        pass

    _DYNAMIC_DOMAIN_CACHE = DEFAULT_DOMAIN
    return _DYNAMIC_DOMAIN_CACHE


def clean_unicode(text):
    """Strips Unicode Private Use Area, missing glyph boxes, and miscellaneous emoji symbols."""
    if not text:
        return ""
    text = re.sub(r"[\ue000-\uf8ff\u2600-\u27bf\ufe00-\ufe0f\ufffd\U0001f300-\U0001f9ff]", " ", text)
    text = re.sub(r"^[\s\-_|#:\*]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_anime_title(text):
    """Cleans anime titles by removing multi-audio, resolution, and download clutter."""
    if not text:
        return ""
    t = clean_unicode(text)

    # 1. Match 'Title (Year)' or 'Title (Season X)'
    m = re.match(r"^(.*?(\((?:19\d\d|20\d\d|Season\s*\d+(?:-\d+)?|S\d+)\)))", t, re.I)
    if m:
        return m.group(1).strip()

    # 2. Match 'Title Season X'
    m_s = re.match(r"^(.*?\b(Season\s*\d+|S\d+)\b)", t, re.I)
    if m_s:
        return m_s.group(1).strip()

    # 3. Strip trailing release and download noise
    t = re.sub(r"\s*(?:Hindi|Tamil|Telugu|English|Japanese|Multi Audio|Episodes Download|Movie Download|Download).*$", "", t, flags=re.I)
    t = re.sub(r"\s*(?:BluRay|WEB-?DL|WEBRip|HDTC|LiNE|NF).*$", "", t, flags=re.I)
    return t.strip(" -_|[]()") if t.strip(" -_|[]()") else text.strip()


def format_quality_label(txt, size=""):
    """Formats quality text into clean streaming options."""
    t = clean_unicode(txt).lower()
    res = "HD"
    if "1080p" in t or "1080" in t:
        res = "1080p Full HD"
    elif "720p" in t or "720" in t:
        res = "720p HD"
    elif "480p" in t or "480" in t:
        res = "480p SD"
    elif "4k" in t or "2160p" in t:
        res = "4K Ultra HD"

    tags = []
    if "10bit" in t:
        tags.append("10Bit")
    if "x265" in t or "hevc" in t:
        tags.append("HEVC")
    elif "x264" in t:
        tags.append("x264")
    if "hq" in t:
        tags.append("HQ")

    tag_str = f" - {' '.join(tags)}" if tags else ""
    size_str = f" ({size})" if size else ""
    return f"[Stream] {res}{tag_str}{size_str}"


class AnimeDubHindiProvider:
    """Faisal0786 AnimeDubHindi Provider ported to native Python for Astra TV."""
    name = "AnimeDubHindi"
    lang = "hi"
    supported_types = ["Anime", "Movie", "TvSeries"]

    @property
    def main_url(self):
        return get_animedub_domain()

    def get_categories(self):
        """Returns primary browsing sections."""
        return [
            ("Latest Anime", "/"),
            ("Hindi Dubbed Anime", "/category/hindi/"),
            ("Anime Movies", "/category/movie/"),
            ("Anime Series", "/category/series/"),
            ("Donghua (Chinese Anime)", "/category/donghua/"),
            ("Action Anime", "/category/action/"),
            ("Adventure Anime", "/category/adventure/"),
            ("Comedy Anime", "/category/comedy/"),
            ("Fantasy & Isekai", "/category/fantasy/"),
            ("Supernatural Anime", "/category/supernatural/"),
            ("Tamil Dubbed", "/category/tamil/"),
            ("Telugu Dubbed", "/category/telugu/")
        ]

    def _fetch_html(self, url, referer=None):
        headers = HEADERS.copy()
        if referer:
            headers["Referer"] = referer

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[AnimeDubHindi] fetch error for {url}: {e}")
            return ""

    def get_items(self, path="", page=1):
        """Scrapes anime catalog cards from category or home page."""
        base = self.main_url
        if not path or path == "/":
            url = f"{base}/page/{page}/" if page > 1 else f"{base}/"
        elif path.startswith("http"):
            url = f"{path.rstrip('/')}/page/{page}/" if page > 1 and "/page/" not in path else path
        else:
            clean_path = path.strip("/")
            url = f"{base}/{clean_path}/page/{page}/" if page > 1 else f"{base}/{clean_path}/"

        html = self._fetch_html(url, referer=f"{base}/")
        if not html:
            return []

        doc = FastHtml(html)
        results = []
        seen = set()

        cards = doc.css("article, .post-thumb, .recent-movies li, div.post")
        for card in cards:
            link_el = card.css_first("a")
            if not link_el:
                continue
            href = link_el.attributes.get("href", "")
            if not href or href in seen or any(x in href for x in ["how-to", "join", "request", "#", "contact"]):
                continue

            if not href.startswith("http"):
                href = f"{base}/{href.lstrip('/')}"
            seen.add(href)

            img_el = card.css_first("img")
            poster = (img_el.attributes.get("src") or img_el.attributes.get("data-src") or "") if img_el else ""

            title_el = card.css_first("h2 a, h3 a, .title a, h2, h3, .title")
            raw_title = title_el.text().strip() if title_el else (img_el.attributes.get("alt", "") if img_el else "")
            if not raw_title:
                continue

            clean_t = clean_anime_title(raw_title)

            # Year extraction
            year_match = re.search(r"\((\d{4})\)", raw_title)
            year = year_match.group(1) if year_match else ""

            # Detect if series or movie
            is_movie = bool(re.search(r"\b(Movie|The Movie)\b", raw_title, re.I)) or "/category/movie/" in path
            is_series = not is_movie

            results.append({
                "title": clean_t,
                "url": href,
                "poster": poster,
                "year": year,
                "is_series": is_series,
                "is_folder": True
            })

        return results

    def search(self, query, page=1):
        """Searches anime on AnimeDubHindi."""
        query = query.strip()
        if not query:
            return []

        base = self.main_url
        search_url = f"{base}/page/{page}/?s={urllib.parse.quote(query)}" if page > 1 else f"{base}/?s={urllib.parse.quote(query)}"
        html = self._fetch_html(search_url, referer=f"{base}/")
        if not html:
            return []

        doc = FastHtml(html)
        results = []
        seen = set()

        cards = doc.css("article, .post-thumb, .recent-movies li, div.post")
        for card in cards:
            link_el = card.css_first("a")
            if not link_el:
                continue
            href = link_el.attributes.get("href", "")
            if not href or href in seen or any(x in href for x in ["how-to", "join", "request", "#", "contact"]):
                continue

            if not href.startswith("http"):
                href = f"{base}/{href.lstrip('/')}"
            seen.add(href)

            img_el = card.css_first("img")
            poster = (img_el.attributes.get("src") or img_el.attributes.get("data-src") or "") if img_el else ""

            title_el = card.css_first("h2 a, h3 a, .title a, h2, h3, .title")
            raw_title = title_el.text().strip() if title_el else ""
            if not raw_title:
                continue

            clean_t = clean_anime_title(raw_title)
            year_match = re.search(r"\((\d{4})\)", raw_title)
            year = year_match.group(1) if year_match else ""

            is_movie = bool(re.search(r"\b(Movie|The Movie)\b", raw_title, re.I))
            is_series = not is_movie

            results.append({
                "title": clean_t,
                "url": href,
                "poster": poster,
                "year": year,
                "is_series": is_series,
                "is_folder": True
            })

        return results

    def load(self, url):
        """Loads an anime detail page and extracts episodes or movie stream options via adhlinks."""
        html = self._fetch_html(url, referer=f"{self.main_url}/")
        if not html:
            return {}

        doc = FastHtml(html)
        title_el = doc.css_first("h1.entry-title, h1.page-title, h1, title")
        raw_title = title_el.text().strip() if title_el else "Anime"
        title = clean_anime_title(raw_title)

        img_el = doc.css_first(".post-thumb img, .entry-content img, article img")
        poster = (img_el.attributes.get("src") or img_el.attributes.get("data-src") or "") if img_el else ""

        # Extract plot / synopsis
        plot_el = doc.css_first(".entry-content p, .synopsis, .description")
        plot = plot_el.text().strip() if plot_el else f"Watch {title} in Hindi Dubbed HD."

        # Find the destination adhlinks URL
        adh_url = None
        for a in doc.css("a"):
            h = a.attributes.get("href", "")
            if "adhlinks.com" in h:
                adh_url = h
                break

        if not adh_url:
            return {
                "title": title,
                "poster": poster,
                "plot": plot,
                "is_series": False,
                "options": []
            }

        # Fetch the adhlinks destination page
        adh_html = self._fetch_html(adh_url, referer=url)
        if not adh_html:
            return {}

        adh_doc = FastHtml(adh_html)
        is_series_page = "/episode/" in adh_url or bool(re.search(r"\b(Season|Episode|Series)\b", raw_title, re.I))

        # ==============================================================================
        # 1. TV Series Episodes Mode
        # ==============================================================================
        episode_groups = adh_doc.css("div.wp-block-group, div.episode-group, div.card")
        episodes = []

        for g in episode_groups:
            txt = g.text().strip()
            ep_match = re.search(r"Episode:?\s*(\d+?)(?:480[pP]|720[pP]|1080[pP]|\D|$)", txt, re.I)
            if not ep_match:
                continue

            ep_num = int(ep_match.group(1))
            ep_name = f"Episode {ep_num}"

            # Extract valid streaming links (hubcloud, gdflix)
            links = []
            seen_links = set()
            for a in g.css("a"):
                h = a.attributes.get("href", "")
                if not h or h in seen_links:
                    continue
                if any(x in h.lower() for x in ["hubcloud", "gdflix"]):
                    seen_links.add(h)
                    links.append(h)

            if links:
                episodes.append({
                    "title": ep_name,
                    "name": ep_name,
                    "url": "|".join(links),
                    "season": 1,
                    "episode": ep_num,
                    "poster": poster,
                    "options": [{
                        "label": f"[Stream] Fast Cloud ({len(links)} mirrors)",
                        "quality": "HD",
                        "urls": links
                    }]
                })

        if episodes:
            episodes.sort(key=lambda x: x["episode"])
            return {
                "title": title,
                "poster": poster,
                "plot": plot,
                "is_series": True,
                "episodes": episodes
            }

        # ==============================================================================
        # 2. Movie Stream Options Mode
        # ==============================================================================
        options = []
        quality_wrappers = adh_doc.css("div.pro-quality-wrapper, div.card, div.download-section")

        for qw in quality_wrappers:
            txt = qw.text().strip()
            links = []
            seen_links = set()
            for a in qw.css("a"):
                h = a.attributes.get("href", "")
                if not h or h in seen_links:
                    continue
                if any(x in h.lower() for x in ["hubcloud", "gdflix"]):
                    seen_links.add(h)
                    links.append(h)

            if links:
                # Extract file size e.g. "500.59 MB" or "1.61 GB"
                size_m = re.search(r"(\d+(?:\.\d+)?\s*(?:GB|MB))\b", txt, re.I)
                size_str = size_m.group(1).upper() if size_m else ""
                label = format_quality_label(txt, size_str)

                options.append({
                    "label": label,
                    "quality": "HD",
                    "urls": links
                })

        # Fallback if wrappers not matched
        if not options:
            seen_links = set()
            for a in adh_doc.css("a"):
                h = a.attributes.get("href", "")
                if not h or h in seen_links:
                    continue
                if any(x in h.lower() for x in ["hubcloud", "gdflix"]):
                    seen_links.add(h)
                    options.append({
                        "label": f"[Stream] Fast Cloud ({len(seen_links)})",
                        "quality": "HD",
                        "urls": [h]
                    })

        return {
            "title": title,
            "poster": poster,
            "plot": f"Stream {title} in Full HD. Direct stream (no download).",
            "is_series": False,
            "options": options
        }
