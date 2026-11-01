# -*- coding: utf-8 -*-
"""
DesiSerialsProvider - Indian TV Serials & Daily Soaps Engine
Replicated from NivinCNC's Cloudstream extension:
https://github.com/NivinCNC/CNCVerse-Cloud-Stream-Extension
Target: https://www.desi-serials.to
Zero external dependencies (uses FastHtml).
"""

import re
import urllib.parse
import urllib.request
import ssl
from resources.lib.core.fast_html import FastHtml
from resources.lib.extractors.tvlogy import TvlogyExtractor

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def clean_title(s):
    if not s:
        return ""
    s = s.replace("\ufffd", " - ").replace("–", "-").replace("—", "-").replace("&ndash;", "-").replace("&mdash;", "-")
    s = re.sub(r"\s*-\s*", " - ", s)
    return " ".join(s.split()).strip()


class DesiSerialsProvider:
    """NivinCNC DesiSerials Provider ported to native Python."""
    name = "DesiSerials"
    lang = "hi"
    supported_types = ["TvSerial"]
    main_url = "https://www.desi-serials.to"

    def __init__(self):
        self.tvlogy = TvlogyExtractor()

    def get_categories(self):
        """Returns primary TV channels as categories."""
        return [
            ("Latest Episodes", "/"),
            ("Star Plus", "/star-plus-hdepisodes/"),
            ("Zee TV", "/zee-tv/"),
            ("Sony TV", "/sony-tv/"),
            ("Colors TV", "/colors-tv/"),
            ("SAB TV", "/sab-tv-hd/"),
            ("Star Bharat", "/star-bharat/"),
            ("&TV", "/and-tv/")
        ]

    def _fetch_html(self, url, referer=None):
        headers = HEADERS.copy()
        if referer:
            headers["Referer"] = referer

        # 1. Try direct fetch
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            pass

        # 2. Fallback via proxy for ISP blocked connections
        try:
            proxy_url = "https://proxy.phisher2.workers.dev/?url=" + url
            req = urllib.request.Request(proxy_url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=12) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[DesiSerialsProvider] fetch error for {url}: {e}")
            return ""

    def get_items(self, path="", page=1):
        """Parses shows or episodes from a channel or show path."""
        if not path or path == "/":
            url = f"{self.main_url}/page/{page}/" if page > 1 else self.main_url
        elif path.startswith("http"):
            url = f"{path}page/{page}/" if page > 1 and not "/page/" in path else path
        else:
            clean_path = path.strip("/")
            url = f"{self.main_url}/{clean_path}/page/{page}/" if page > 1 else f"{self.main_url}/{clean_path}/"

        html = self._fetch_html(url)
        if not html:
            return []

        doc = FastHtml(html)
        results = []
        seen = set()

        cards = doc.css("article.type-post, article.post-grid, .porto-sicon-wrapper, li.cat-item, .post-item")
        for card in cards:
            link_el = card.css_first("h3.thumb-info-inner a, h2.entry-title a, h5 a.porto-sicon-title-link, h3.porto-post-title a, a")
            img_el = card.css_first("div.post-image img, span.post-image img, .porto-sicon-img img, div.page-image img, img")

            if not link_el:
                continue

            href = link_el.attributes.get("href", "").strip()
            if not href or href in seen:
                continue

            # Skip header menus and external links
            if not href.startswith("http") or any(x in href for x in ["facebook.com", "twitter.com", "pinterest.com", "/contact-us"]):
                continue

            seen.add(href)
            title = clean_title(link_el.text().strip())
            if not title:
                title = clean_title((img_el.attributes.get("alt") if img_el else "") or (link_el.attributes.get("title") or ""))
                if not title:
                    slug = href.rstrip("/").split("/")[-1]
                    title = clean_title(slug.replace("-", " ").title())

            poster = ""
            if img_el:
                poster = img_el.attributes.get("data-src") or img_el.attributes.get("src") or ""
                if poster and not poster.startswith("http"):
                    poster = f"{self.main_url}/{poster.lstrip('/')}"

            is_show_folder = any(x in href for x in ["/watch-online/", "/category/", "-hdepisodes", "/zee-tv/", "/sony-tv/", "/colors-tv/", "/sab-tv-hd/"]) and not "episode" in href.lower()

            results.append({
                "title": title,
                "url": href,
                "poster": poster,
                "provider": self.name,
                "is_series": True,
                "is_folder": is_show_folder
            })

        return results

    def search(self, query, page=1):
        """Searches desi-serials for query."""
        encoded = urllib.parse.quote(query)
        url = f"{self.main_url}/page/{page}/?s={encoded}" if page > 1 else f"{self.main_url}/?s={encoded}"

        html = self._fetch_html(url)
        if not html:
            return []

        doc = FastHtml(html)
        results = []
        seen = set()

        cards = doc.css("article.type-post, article.post-grid, div.post-item")
        for card in cards:
            link_el = card.css_first("h3.thumb-info-inner a, h2.entry-title a, h5 a.porto-sicon-title-link, a")
            img_el = card.css_first("img")

            if not link_el:
                continue

            href = link_el.attributes.get("href", "").strip()
            if not href or href in seen or not href.startswith("http"):
                continue

            seen.add(href)
            title = link_el.text().strip()
            poster = (img_el.attributes.get("data-src") or img_el.attributes.get("src") or "") if img_el else ""

            is_show_folder = "/watch-online/" in href and not "episode" in href.lower()

            results.append({
                "title": title,
                "url": href,
                "poster": poster,
                "provider": self.name,
                "is_series": True,
                "is_folder": is_show_folder
            })

        return results

    def load(self, url, page=1):
        """
        Loads either:
        1. A show folder -> returns list of episodes on specified page + max_page.
        2. An episode page -> extracts streaming video host options.
        """
        clean_url = url.rstrip("/")
        page_int = int(page) if str(page).isdigit() else 1
        if page_int > 1 and not "/page/" in clean_url:
            fetch_url = f"{clean_url}/page/{page_int}/"
        else:
            fetch_url = url

        html = self._fetch_html(fetch_url)
        if not html:
            return {}

        doc = FastHtml(html)
        title_el = doc.css_first("h1.page-title, h1.entry-title, h1, title")
        title = title_el.text().strip() if title_el else "Episode"
        title = re.sub(r"\s*-\s*Desi-Serials\.TO.*", "", title, flags=re.I)

        img_el = doc.css_first("div.post-image img, span.post-image img, div.page-image img, img")
        page_poster = (img_el.attributes.get("data-src") or img_el.attributes.get("src") or "") if img_el else ""
        if page_poster and not "logo" in page_poster.lower():
            if not page_poster.startswith("http"):
                page_poster = f"{self.main_url}/{page_poster.lstrip('/')}"
            poster = page_poster
        else:
            poster = ""

        # Parse pagination max_page
        page_numbers = []
        for p in doc.css("a.page-numbers, span.page-numbers"):
            txt = p.text().strip()
            if txt.isdigit():
                page_numbers.append(int(txt))
        max_page = max(page_numbers) if page_numbers else 1

        # Check if episode page has video links
        links = doc.css("div.entry-content p a, div.entry-content a")
        video_host_urls = []
        for a in links:
            href = a.attributes.get("href", "")
            if any(s in href.lower() for s in ["tumblr", "facebook", "twitter", "whatsapp", "pinterest", "reddit"]):
                continue
            if any(x in href.lower() for x in ["tvarticles.org", "vidd", "flow.tvlogy", "playdesi", "vkprime", "vkspeed"]):
                if href not in video_host_urls:
                    video_host_urls.append(href)

        # Fallback iframe search (case-insensitive regex for uppercase <IFRAME SRC=...>)
        for ifr_src in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
            if any(x in ifr_src.lower() for x in ["tvlogy", "tvarticles", "vkprime", "vkspeed"]):
                if ifr_src not in video_host_urls:
                    video_host_urls.append(ifr_src)

        # Case A: If video links exist -> It's an episode playback page!
        if video_host_urls:
            options = []
            for idx, host_url in enumerate(video_host_urls[:5], 1):
                srv_name = "VkPrime" if "vkprime" in host_url.lower() else ("VkSpeed" if "vkspeed" in host_url.lower() else "Server")
                options.append({
                    "label": f"Server {idx} ({srv_name})",
                    "quality": "HD",
                    "urls": [host_url]
                })
            return {
                "title": title,
                "poster": poster,
                "plot": f"Stream {title} in HD",
                "is_series": True,
                "options": options
            }

        # Case B: If no video links but cards exist -> It's a show folder listing episodes!
        episode_cards = doc.css("article.type-post, article.post-grid, div.post-item")
        episodes = []
        for card in episode_cards:
            a = card.css_first("h3.thumb-info-inner a, h2.entry-title a, a")
            im = card.css_first("img")
            if a and a.attributes.get("href"):
                ep_href = a.attributes.get("href")
                if not any(x in ep_href for x in ["facebook.com", "twitter.com", "pinterest.com", "/contact-us"]):
                    ep_img = ""
                    if im:
                        ep_img = im.attributes.get("data-src") or im.attributes.get("src") or ""
                        if ep_img and not ep_img.startswith("http"):
                            ep_img = f"{self.main_url}/{ep_img.lstrip('/')}"
                        if "logo" in ep_img.lower():
                            ep_img = ""
                    
                    cleaned_name = clean_title(a.text().strip())
                    yr_match = re.search(r'(20\d\d)', cleaned_name)
                    ep_season = int(yr_match.group(1)) if yr_match else 2026

                    episodes.append({
                        "name": cleaned_name,
                        "url": ep_href,
                        "poster": ep_img or poster,
                        "episode": len(episodes) + 1,
                        "season": ep_season
                    })

        return {
            "title": title,
            "poster": poster,
            "plot": f"Watch episodes of {title}",
            "is_series": True,
            "max_page": max_page,
            "page": page_int,
            "episodes": episodes,
            "options": []
        }

    def get_all_episodes(self, url):
        """
        Loads all episodes in chronological order (Episode 1, 2, ... N),
        matching CloudStream's exact episode list structure.
        Uses ThreadPoolExecutor for fast parallel retrieval and caches results.
        """
        if not hasattr(self, "_ep_cache"):
            self._ep_cache = {}
        if url in self._ep_cache:
            return self._ep_cache[url]

        first_page = self.load(url, page=1)
        if not first_page:
            return {}

        max_page = first_page.get("max_page", 1)
        if max_page == 1:
            eps = list(reversed(first_page.get("episodes", [])))
            for idx, ep in enumerate(eps, 1):
                ep["episode"] = idx
            first_page["all_episodes"] = eps
            first_page["total_episodes"] = len(eps)
            self._ep_cache[url] = first_page
            return first_page

        from concurrent.futures import ThreadPoolExecutor

        if max_page <= 30:
            def _fetch_p(p):
                return p, self.load(url, page=p).get("episodes", [])

            with ThreadPoolExecutor(max_workers=min(max_page, 12)) as executor:
                pages_dict = dict(executor.map(_fetch_p, range(1, max_page + 1)))

            all_eps = []
            for p in range(max_page, 0, -1):
                cards = pages_dict.get(p, [])
                all_eps.extend(reversed(cards))

            for idx, ep in enumerate(all_eps, 1):
                ep["episode"] = idx

            first_page["all_episodes"] = all_eps
            first_page["total_episodes"] = len(all_eps)
            self._ep_cache[url] = first_page
            return first_page

        # For massive daily soaps (> 30 pages): estimate total episodes
        first_page["total_episodes"] = max_page * 15
        self._ep_cache[url] = first_page
        return first_page

    def get_chunk_episodes(self, url, start_ep, end_ep):
        """Returns episodes within [start_ep, end_ep]."""
        data = self.get_all_episodes(url)
        all_eps = data.get("all_episodes", [])
        if all_eps:
            return all_eps[start_ep - 1 : end_ep]

        # For shows with > 30 pages where all_episodes wasn't preloaded:
        max_page = data.get("max_page", 1)
        total_ep = max_page * 15
        p_start = max(1, max_page - (end_ep // 15))
        p_end = min(max_page, max_page - ((start_ep - 1) // 15) + 1)
        
        pages_to_fetch = list(range(p_start, p_end + 1))
        from concurrent.futures import ThreadPoolExecutor
        def _fetch_p(p):
            return p, self.load(url, page=p).get("episodes", [])

        with ThreadPoolExecutor(max_workers=len(pages_to_fetch)) as executor:
            pages_dict = dict(executor.map(_fetch_p, pages_to_fetch))

        collected = []
        for p in sorted(pages_to_fetch, reverse=True):
            collected.extend(reversed(pages_dict.get(p, [])))

        for idx, ep in enumerate(collected, start_ep):
            ep["episode"] = idx
        return collected[: end_ep - start_ep + 1]

    def load_links(self, data_url):
        """Extracts direct playable stream from video host URL."""
        return self.tvlogy.extract(data_url)
