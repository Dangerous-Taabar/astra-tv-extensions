# -*- coding: utf-8 -*-
"""
HDhub4u Provider - High-Speed Movies & Web Series Engine
Replicated from Phisher98's Cloudstream extension:
https://github.com/phisher98/cloudstream-extensions-phisher
Zero external dependencies (uses FastHtml).
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

DEFAULT_DOMAIN = "https://new10.hdhub4u.cl"
_DYNAMIC_DOMAIN_CACHE = None


def get_hdhub_domain():
    """Fetches latest unblocked HDHub4u domain from Phisher98's live domains map."""
    global _DYNAMIC_DOMAIN_CACHE
    if _DYNAMIC_DOMAIN_CACHE:
        return _DYNAMIC_DOMAIN_CACHE

    try:
        url = "https://raw.githubusercontent.com/phisher98/TVVVV/refs/heads/main/domains.json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
            domain = data.get("HDHUB4u", DEFAULT_DOMAIN).rstrip("/")
            if domain.startswith("http"):
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
    text = re.sub(r"[\ue000-\uf8ff\u2600-\u27bf\ufe00-\ufe0f\ufffd]", " ", text)
    text = re.sub(r"^[\s\-_|#:\*]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_movie_title(text):
    """Cleans movie and series titles by removing audio, quality, and release clutter."""
    if not text:
        return ""
    t = clean_unicode(text)

    # 1. Match 'Title (Year)' or 'Title (Season X)'
    m = re.match(r"^(.*?(\((?:19\d\d|20\d\d|Season\s*\d+(?:-\d+)?|S\d+)\)))", t, re.I)
    if m:
        return m.group(1).strip()

    # 2. Match standalone year 'Title 2024'
    m_yr = re.match(r"^(.*?\b(19\d\d|20\d\d)\b)", t)
    if m_yr:
        pre = m_yr.group(1).strip()
        yr = m_yr.group(2)
        base = pre[:-len(yr)].strip(" -_")
        if base:
            return f"{base} ({yr})"

    # 3. Match 'Title Season X'
    m_s = re.match(r"^(.*?\b(Season\s*\d+|S\d+)\b)", t, re.I)
    if m_s:
        pre = m_s.group(1).strip()
        s_part = m_s.group(2).strip()
        base = pre[:-len(s_part)].strip(" -_")
        if base:
            return f"{base} ({s_part})"
        return pre

    # 4. Fallback cutoff before release/format junk
    cutoff = r"\b(bluray|web-?dl|webrip|hdrip|dvdrip|hdtc|pre-?dvdrip|1080p|720p|480p|4k|2160p|dual audio|multi audio|hindi|trailer)\b.*$"
    t_clean = re.sub(cutoff, "", t, flags=re.I).strip(" -_|[]()")
    return t_clean if t_clean else t


def format_stream_label(raw_text, href=""):
    """Formats raw scraper button text into clean, crystal-clear streaming options."""
    txt = clean_unicode(raw_text)
    lower_txt = txt.lower()
    lower_href = href.lower()

    # 1. Instant Watch Online Web Player
    if re.search(r"\b(watch\s*online|watch)\b", lower_txt) or "hdstream" in lower_href:
        return "[Watch Online] Instant Stream (Fast Server)"

    # 2. Extract File Size if present (e.g. 840MB, 1.7GB, 35GB, 27GB)
    size_match = re.search(r"(\d+(?:\.\d+)?\s*(?:GB|MB))\b", txt, re.I)
    size_str = f" ({size_match.group(1).upper()})" if size_match else ""

    # 3. Detect Resolution
    res = ""
    if re.search(r"\b(4k|2160p)\b", lower_txt) or "4k" in lower_href or "2160p" in lower_href:
        res = "4K Ultra HD"
    elif re.search(r"\b1080p\b", lower_txt) or "1080p" in lower_href:
        res = "1080p Full HD"
    elif re.search(r"\b720p\b", lower_txt) or "720p" in lower_href:
        res = "720p HD"
    elif re.search(r"\b480p\b", lower_txt) or "480p" in lower_href:
        res = "480p SD"

    # 4. Detect Source & Codec
    tags = []
    if re.search(r"\bbluray\b", lower_txt):
        tags.append("BluRay Master")
    elif re.search(r"\bweb-?dl\b", lower_txt):
        tags.append("WEB-DL")
    elif re.search(r"\bwebrip\b", lower_txt):
        tags.append("WEBRip")
    elif re.search(r"\bhdtc\b", lower_txt):
        tags.append("HDTC")

    if re.search(r"\bmulti\b", lower_txt):
        if "WEB-DL" in tags:
            tags[tags.index("WEB-DL")] = "WEB-DL Multi-Audio"
        elif "WEBRip" in tags:
            tags[tags.index("WEBRip")] = "WEBRip Multi-Audio"
        else:
            tags.append("Multi-Audio")

    if re.search(r"\b10bit\b", lower_txt):
        if re.search(r"\bhevc\b", lower_txt):
            tags.append("10Bit HEVC")
        else:
            tags.append("10Bit")
    elif re.search(r"\bhevc\b", lower_txt):
        tags.append("HEVC")
    elif re.search(r"\bx264\b", lower_txt):
        tags.append("x264")
    elif re.search(r"\bx265\b", lower_txt):
        tags.append("x265")

    tag_str = f" - {' '.join(tags)}" if tags else ""

    if res:
        return f"[Stream] {res}{tag_str}{size_str}"
    elif tags:
        return f"[Stream] {' '.join(tags)}{size_str}"
    else:
        clean_name = re.sub(r"[\[\]]+", " ", txt)
        clean_name = re.sub(r"\s+", " ", clean_name).strip()
        if not clean_name:
            clean_name = "Cloud Server"
        return f"[Stream] {clean_name}{size_str}"


class HDhub4uProvider:
    """Phisher98 HDHub4u Provider ported to native Python for Astra TV."""
    name = "HDhub4u"
    lang = "hi"
    supported_types = ["Movie", "TvSeries", "Anime"]

    @property
    def main_url(self):
        return get_hdhub_domain()

    def get_categories(self):
        """Returns primary browsing sections."""
        return [
            ("Latest Movies & Series", "/"),
            ("Bollywood Movies", "/category/bollywood-movies/"),
            ("Hollywood Movies", "/category/hollywood-movies/"),
            ("Hindi Dubbed", "/category/hindi-dubbed/"),
            ("South Hindi Dubbed", "/category/south-hindi-movies/"),
            ("Web Series", "/category/category/web-series/"),
            ("300MB Movies", "/category/300mb-movies/"),
            ("WWE Wrestling", "/category/wrestling-shows/"),
        ]

    def _fetch_html(self, url, referer=None):
        headers = HEADERS.copy()
        if referer:
            headers["Referer"] = referer

        # 1. Direct fetch
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            pass

        # 2. Proxy fallback for ISP blocks
        try:
            proxy_url = "https://proxy.phisher2.workers.dev/?url=" + url
            req = urllib.request.Request(proxy_url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[HDhub4uProvider] fetch error for {url}: {e}")
            return ""

    def get_items(self, path="", page=1):
        """Scrapes catalog cards from category or home page."""
        base = self.main_url
        if not path or path == "/":
            url = f"{base}/page/{page}/" if page > 1 else f"{base}/"
        elif path.startswith("http"):
            url = f"{path.rstrip('/')}/page/{page}/" if page > 1 and not "/page/" in path else path
        else:
            clean_path = path.strip("/")
            url = f"{base}/{clean_path}/page/{page}/" if page > 1 else f"{base}/{clean_path}/"

        html = self._fetch_html(url, referer=f"{base}/")
        if not html:
            return []

        doc = FastHtml(html)
        results = []
        seen = set()

        cards = doc.css("ul.recent-movies li, div.recent-movies li, article, .thumb, .home-post, figure")
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

            title_el = card.css_first("figcaption, p, h2, h3, .title")
            raw_title = title_el.text().strip() if title_el else (img_el.attributes.get("alt", "") if img_el else "")
            clean_t = clean_movie_title(raw_title)

            if not clean_t:
                continue

            # Detect year
            year_match = re.search(r"\((\d{4})\)", clean_t)
            year = year_match.group(1) if year_match else ""

            # Detect if series
            is_series = bool(re.search(r"\b(Season|Series|S\d+|EP|Episodes)\b", clean_t, re.I))

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
        """Searches HDHub4u using high-speed Pingora Typesense API with HTML fallback."""
        query = query.strip()
        if not query:
            return []

        base = self.main_url
        results = []

        # 1. Try Pingora Typesense API (Instant indexed search used by CloudStream)
        try:
            api_url = (
                f"https://search.pingora.fyi/collections/post/documents/search?"
                f"q={urllib.parse.quote(query)}"
                f"&query_by=post_title,category,stars,director,imdb_id"
                f"&query_by_weights=4,2,2,2,4"
                f"&sort_by=sort_by_date:desc"
                f"&limit=15&highlight_fields=none&use_cache=true"
                f"&page={page}"
            )
            headers = HEADERS.copy()
            headers["Referer"] = f"{base}/"
            headers["Origin"] = base

            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as r:
                data = json.loads(r.read().decode("utf-8", "ignore"))
                for hit in data.get("hits", []):
                    doc = hit.get("document", {})
                    p_title = clean_movie_title(doc.get("post_title", ""))
                    p_url = doc.get("permalink", "")
                    p_thumb = doc.get("post_thumbnail", "")
                    if p_title and p_url:
                        # Extract year
                        year_match = re.search(r"\((\d{4})\)", p_title)
                        year = year_match.group(1) if year_match else ""
                        is_series = bool(re.search(r"\b(Season|Series|S\d+|EP)\b", p_title, re.I))
                        results.append({
                            "title": p_title,
                            "url": p_url,
                            "poster": p_thumb,
                            "year": year,
                            "is_series": is_series,
                            "is_folder": True
                        })
                if results:
                    return results
        except Exception:
            pass

        # 2. Fallback to HTML Search
        search_url = f"{base}/page/{page}/?s={urllib.parse.quote(query)}" if page > 1 else f"{base}/?s={urllib.parse.quote(query)}"
        html = self._fetch_html(search_url, referer=f"{base}/")
        if not html:
            return []

        doc = FastHtml(html)
        seen = set()
        cards = doc.css("ul.recent-movies li, div.recent-movies li, article, .thumb, .home-post, figure")
        for card in cards:
            link_el = card.css_first("a")
            if not link_el:
                continue
            href = link_el.attributes.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            img_el = card.css_first("img")
            poster = (img_el.attributes.get("src") or img_el.attributes.get("data-src") or "") if img_el else ""

            title_el = card.css_first("figcaption, p, h2, h3, .title")
            raw_title = clean_movie_title(title_el.text().strip() if title_el else "")
            if not raw_title:
                continue

            year_match = re.search(r"\((\d{4})\)", raw_title)
            year = year_match.group(1) if year_match else ""
            is_series = bool(re.search(r"\b(Season|Series|S\d+|EP)\b", raw_title, re.I))

            results.append({
                "title": raw_title,
                "url": href,
                "poster": poster,
                "year": year,
                "is_series": is_series,
                "is_folder": True
            })

        return results

    def load(self, url):
        """Loads a movie or series detail page and extracts stream options or episodes."""
        html = self._fetch_html(url, referer=f"{self.main_url}/")
        if not html:
            return {}

        doc = FastHtml(html)
        title_el = doc.css_first("h1.page-title, h1.entry-title, h1, title")
        raw_title = title_el.text().strip() if title_el else "Movie"
        raw_title = re.sub(r"\s*\|\s*HDHub4u.*", "", raw_title, flags=re.I).strip()
        title = clean_movie_title(raw_title)

        img_el = doc.css_first("div.entry-content img, .post-thumbnail img, img.aligncenter, img")
        poster = (img_el.attributes.get("src") or img_el.attributes.get("data-src") or "") if img_el else ""

        is_series = bool(re.search(r"\b(Season|Series|Episodes|EP-\d+)\b", title, re.I))

        # Check for TV Series Episodes layout
        episode_blocks = []
        for p in doc.css("p, h3, h4, div.entry-content > *, .page-body > *"):
            text = p.text().strip()
            ep_match = re.search(r"(?:EPiSODE|Episode|EP)\s*(\d+)", text, re.I)
            if ep_match:
                links = [a.attributes.get("href") for a in p.css("a") if a.attributes.get("href")]
                valid_links = [l for l in links if any(x in l.lower() for x in ["hdstream", "hubdrive", "greenmotors", "hubcloud", "vidaraa", "hubcdn", "hblinks"])]
                if valid_links:
                    ep_num = int(ep_match.group(1))
                    episode_blocks.append((ep_num, f"Episode {ep_num}", valid_links))

        if is_series and episode_blocks:
            # Series Mode: Return episodes list
            episodes = []
            for num, ep_title, links in sorted(episode_blocks, key=lambda x: x[0]):
                ep_clean = clean_unicode(ep_title)
                episodes.append({
                    "title": ep_clean,
                    "name": ep_clean,
                    "url": "|".join(links),
                    "season": 1,
                    "episode": num,
                    "poster": poster,
                    "options": [{
                        "label": f"[Stream] Fast Cloud ({len(links)} mirrors)",
                        "quality": "HD",
                        "urls": links
                    }]
                })
            return {
                "title": title,
                "poster": poster,
                "plot": f"Watch {title} in Full HD",
                "is_series": True,
                "episodes": episodes
            }

        # Movie Mode: Extract all stream buttons and qualities
        options = []
        buttons = []
        seen_urls = set()
        for a in doc.css("a"):
            h = a.attributes.get("href", "")
            if not h or h in seen_urls:
                continue
            if any(x in h.lower() for x in ["hubdrive", "hdstream", "hubcdn", "hubcloud", "greenmotors", "hblinks"]):
                seen_urls.add(h)
                buttons.append(a)

        for b in buttons:
            h = b.attributes.get("href", "")
            txt = b.text().strip()
            label = format_stream_label(txt, h)

            options.append({
                "label": label,
                "quality": "HD",
                "urls": [h]
            })

        return {
            "title": title,
            "poster": poster,
            "plot": f"Stream {title} directly online. All options stream instantly in Kodi player (no storage download needed).",
            "is_series": False,
            "options": options
        }

