# -*- coding: utf-8 -*-
"""
LivXow Provider for Astra TV
Ported from CloudStream com.cncverse.LivXowProvider (Kotlin).
Provides Live Sports, Cricket, and TV Channels with Firebase remote config, custom cipher, and ClearKey DRM.
"""

import json
import base64
import urllib.request
import urllib.parse
import ssl
import re

try:
    from resources.lib.aes import AES
except ImportError:
    try:
        from aes import AES
    except ImportError:
        AES = None

# Secure runtime de-obfuscator for credentials
_u = lambda s: bytes([b ^ 0x73 for b in base64.b64decode(s)]).decode('utf-8')

# Masked Remote Config & Cipher Credentials
FIREBASE_API_KEY = _u("MjoJEiAKMToVGSsCHx5BIj8/EAcdJyYiJj04ShlKOBVBChEgRAoE")
FIREBASE_APP_ID = _u("QklHRkpGQEpASktFQERJEh0XARwaF0lKRUFEQ0JBRxcVR0tKREISFUJAQhZH")
FIREBASE_PROJECT_NUMBER = _u("R0ZKRkBKQEpLRUBE")
PACKAGE_NAME = _u("EBweXR8aBQscBF0HBQ==")
DEFAULT_BASE_URL = _u("GwcHAwBJXFwAHBsAGRwXGxYUABoWGRYbXQAbHAM=")

STANDARD_ALPHABET = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ"
SHUFFLED_ALPHABET = "fFgGjJkKaApPbBmMoOzZeEnNcCdDrRqQtTvVuUxXhHiIwWyYlLsS"
AES_KEY = b"M8mkKlNL75K4nl15"
AES_IV = b"kN7m5Kl1pN5nk4xK"

DECODE_TABLE = {i: i for i in range(128)}
for i in range(len(STANDARD_ALPHABET)):
    DECODE_TABLE[ord(SHUFFLED_ALPHABET[i])] = ord(STANDARD_ALPHABET[i])

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def decrypt_substitution(text):
    """Reverses the custom alphabet shuffle."""
    return "".join(chr(DECODE_TABLE[ord(c)]) if ord(c) < 128 else c for c in text)


def decrypt_http_response(text):
    """Decryption: Substitution -> Base64 -> AES-128-CBC -> PKCS7 unpad."""
    if not text:
        return ""
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        return text

    try:
        substituted = decrypt_substitution(text)
        if len(substituted) % 4 != 0:
            substituted += "=" * (4 - (len(substituted) % 4))
        decoded_bytes = base64.b64decode(substituted)

        if AES is not None:
            aes = AES(AES_KEY, AES_IV)
            decrypted_bytes = aes.decrypt(decoded_bytes)
            if decrypted_bytes:
                # Correct PKCS7 unpadding
                pad_len = decrypted_bytes[-1]
                if 1 <= pad_len <= 16 and all(b == pad_len for b in decrypted_bytes[-pad_len:]):
                    decrypted_bytes = decrypted_bytes[:-pad_len]
                return decrypted_bytes.decode('utf-8', errors='ignore').strip()
    except Exception as e:
        print(f"[LivXow] Decryption notice: {e}")
    return ""


def fetch_url(url, headers=None, data=None, timeout=7):
    if not url or not url.startswith("http"):
        return None
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception:
        return None


def get_firebase_config():
    """Fetches dynamic API base URL from Firebase Remote Config."""
    url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{FIREBASE_PROJECT_NUMBER}/namespaces/firebase:fetch"
    payload = {
        "appVersion": "2.3",
        "timeZone": "Asia/Calcutta",
        "appInstanceIdToken": "",
        "languageCode": "en-IN",
        "appBuild": "5",
        "appInstanceId": "e8oXwurwSlyewCIEp8rdgs",
        "countryCode": "IN",
        "analyticsUserProperties": {},
        "appId": FIREBASE_APP_ID,
        "platformVersion": "33",
        "sdkVersion": "23.1.0",
        "packageName": PACKAGE_NAME
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Android-Package": PACKAGE_NAME,
        "X-Goog-Api-Key": FIREBASE_API_KEY,
        "X-Google-GFE-Can-Retry": "yes"
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            entries = res_json.get("entries", {})
            api_url = entries.get("api_url")
            if api_url:
                return api_url.rstrip("/")
    except Exception:
        pass
    return DEFAULT_BASE_URL


def parse_m3u(text):
    """Parses M3U playlist lines extracting channels, headers, and DRM props."""
    channels = []
    current = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            try:
                info_part, title = line.rsplit(",", 1)
                current["title"] = title.strip()
                logo_match = re.search(r'tvg-logo="([^"]+)"', info_part)
                if logo_match:
                    current["poster"] = logo_match.group(1)
                group_match = re.search(r'group-title="([^"]+)"', info_part)
                if group_match:
                    current["group"] = group_match.group(1)
            except Exception:
                current["title"] = line
            current["headers"] = {}
            current["drm"] = {}
        elif line.startswith("#EXTVLCOPT:"):
            opt = line.replace("#EXTVLCOPT:", "").strip()
            if "=" in opt:
                k, v = opt.split("=", 1)
                k = k.lower().strip()
                if "user-agent" in k:
                    current["headers"]["User-Agent"] = v.strip()
                elif "referer" in k or "referrer" in k:
                    current["headers"]["Referer"] = v.strip()
                elif "cookie" in k:
                    current["headers"]["Cookie"] = v.strip()
        elif line.startswith("#EXTHTTP:"):
            try:
                headers_json = line.replace("#EXTHTTP:", "").strip()
                headers = json.loads(headers_json)
                if isinstance(headers, dict):
                    current["headers"].update(headers)
            except Exception:
                pass
        elif line.startswith("#KODIPROP:"):
            prop = line.replace("#KODIPROP:", "").strip()
            if "license_key=" in prop:
                current["drm"]["license_key"] = prop.split("license_key=", 1)[1].strip()
            elif "manifest_type=" in prop:
                current["drm"]["manifest_type"] = prop.split("manifest_type=", 1)[1].strip()
        elif not line.startswith("#"):
            if current.get("title"):
                current["url"] = line
                channels.append(current)
                current = {}
    return channels


class LivXowProvider:
    name = "LivXow"
    lang = "en"
    supported_types = ["LiveStream", "Live"]
    version = 1

    def __init__(self):
        self.base_url = None

    def _get_base_url(self):
        if not self.base_url:
            self.base_url = get_firebase_config()
        return self.base_url

    def get_categories(self):
        """Returns clean sport categories and active TV channels."""
        return [
            ("[Sports] Live Cricket Matches", "special://events?sport=Cricket"),
            ("[Sports] Live Football Matches", "special://events?sport=Football"),
            ("[Sports] Boxing & WWE Events", "special://events?sport=Boxing"),
            ("[Sports] Basketball Games", "special://events?sport=Basketball"),
            ("[Sports] Motorsport & F1", "special://events?sport=Motorsport"),
            ("[Sports] Tennis Tournaments", "special://events?sport=Tennis"),
            ("[Sports] American Football (NFL)", "special://events?sport=American football"),
            ("[Sports] Hockey Matches", "special://events?sport=Hockey"),
            ("[Sports] All Live & Upcoming Matches", "special://events"),
            ("[Live TV] 24/7 Sports Channels", "cat://custom/channels/U1BPUlRTMTc3Mjc2NTI3ODI3Mw.txt"),
        ]

    def get_items(self, path="", page=1):
        """Fetches items for categories, events, or channel server lists."""
        if not path:
            return []

        base = self._get_base_url()
        default_logo = "https://raw.githubusercontent.com/recloudstream/extensions/master/img/live.png"

        # 1. Live Events List (Matches filtered by sport)
        if path.startswith("special://events"):
            parsed_path = urllib.parse.urlparse(path)
            q_sport = urllib.parse.parse_qs(parsed_path.query).get("sport", [None])[0]

            res = fetch_url(f"{base}/events.txt")
            if not res:
                return []
            dec = decrypt_http_response(res)
            items = []
            try:
                data = json.loads(dec)
                parsed_events = []
                for item in data:
                    ev = json.loads(item.get("event", "{}"))
                    cat = ev.get("category", "")
                    if q_sport and cat.lower() != q_sport.lower():
                        continue
                    parsed_events.append(ev)

                # Prioritize Live matches (priority == 1) at the top, then upcoming matches
                parsed_events.sort(key=lambda x: x.get("priority", -1), reverse=True)

                for ev in parsed_events:
                    prio = ev.get("priority", -1)
                    badge = "[• LIVE]" if prio == 1 else "[• UPCOMING]"
                    ev_name = ev.get("eventName", "Match")
                    team_a = ev.get("teamAName", "")
                    team_b = ev.get("teamBName", "")
                    time_str = ev.get("time", "")

                    if team_a and team_b:
                        title = f"{badge} {team_a} vs {team_b} ({ev_name}) [{time_str}]"
                    elif team_a:
                        title = f"{badge} {team_a} ({ev_name}) [{time_str}]"
                    else:
                        title = f"{badge} {ev_name} [{time_str}]"

                    links_rel = ev.get("links", "")
                    if not links_rel:
                        continue

                    logo = ev.get("teamBFlag") or ev.get("teamAFlag") or ev.get("eventLogo") or default_logo
                    event_url = f"special://event_links?path={urllib.parse.quote(links_rel)}&title={urllib.parse.quote(title)}"

                    items.append({
                        "title": title,
                        "url": event_url,
                        "poster": logo,
                        "is_live": False,
                        "is_folder": True,
                        "is_series": False
                    })
            except Exception as e:
                print(f"[LivXow] Events parse error: {e}")
            return items

        # 2. Match or Channel Direct Stream Servers
        if path.startswith("special://event_links"):
            parsed = urllib.parse.urlparse(path)
            q = urllib.parse.parse_qs(parsed.query)
            links_rel = q.get("path", [""])[0]
            if not links_rel:
                return []
            url = f"{base}/{links_rel}" if not links_rel.startswith("http") else links_rel
            res = fetch_url(url)
            if not res:
                return []
            dec = decrypt_http_response(res)
            items = []
            try:
                data = json.loads(dec)
                for srv in data:
                    srv_name = srv.get("name", "Stream")
                    tag = srv.get("linkTag", "HD")
                    label = f"▶ {srv_name} [{tag}]"
                    raw_link = srv.get("link", "")
                    if not raw_link:
                        continue

                    # Parse headers from pipe |
                    clean_link = raw_link
                    headers = {}
                    if "|" in raw_link:
                        parts = raw_link.split("|", 1)
                        clean_link = parts[0]
                        for h in parts[1].split("&"):
                            if "=" in h:
                                hk, hv = h.split("=", 1)
                                headers[hk.strip()] = urllib.parse.unquote(hv.strip())

                    # ClearKey DRM
                    drm_info = {}
                    key_val = srv.get("api")
                    if key_val:
                        drm_info = {
                            "license_key": key_val,
                            "manifest_type": "mpd" if ".mpd" in clean_link else "hls"
                        }

                    payload = {
                        "title": label,
                        "url": clean_link,
                        "headers": headers,
                        "drm": drm_info,
                        "is_live": True
                    }

                    items.append({
                        "title": label,
                        "url": json.dumps(payload),
                        "poster": default_logo,
                        "is_live": True,
                        "is_folder": False,
                        "is_series": False
                    })
            except Exception as e:
                print(f"[LivXow] Links parse error: {e}")
            return items

        # 3. Custom Category (Channels list)
        if path.startswith("cat://custom/"):
            rel_api = path.replace("cat://custom/", "")
            url = f"{base}/{rel_api}" if not rel_api.startswith("http") else rel_api
            res = fetch_url(url)
            if not res:
                return []
            dec = decrypt_http_response(res)
            items = []
            try:
                data = json.loads(dec)
                for item in data:
                    ch = json.loads(item.get("channel", "{}"))
                    ch_name = ch.get("name", "Channel")
                    ch_links = ch.get("links", "")
                    if not ch_links:
                        continue
                    ch_logo = ch.get("logo") or default_logo
                    ch_url = f"special://event_links?path={urllib.parse.quote(ch_links)}&title={urllib.parse.quote(ch_name)}"
                    items.append({
                        "title": f"[Channel] {ch_name}",
                        "url": ch_url,
                        "poster": ch_logo,
                        "is_live": False,
                        "is_folder": True,
                        "is_series": False
                    })
            except Exception as e:
                print(f"[LivXow] Custom channel parse error: {e}")
            return items

        # 4. Standard M3U Playlist
        target_m3u_url = path.replace("cat://m3u/", "") if path.startswith("cat://m3u/") else path
        res = fetch_url(target_m3u_url)
        if not res:
            return []

        dec = decrypt_http_response(res) if (not res.startswith("#EXTM3U") and "#EXTINF" not in res) else res
        channels = parse_m3u(dec)
        items = []
        for ch in channels:
            title = ch.get("title", "Live Channel").strip()
            ch_url = ch.get("url", "").strip()
            if not ch_url:
                continue
            payload = {
                "title": title,
                "url": ch_url,
                "headers": ch.get("headers", {}),
                "drm": ch.get("drm", {}),
                "is_live": True
            }
            items.append({
                "title": title,
                "url": json.dumps(payload),
                "poster": ch.get("poster") or default_logo,
                "group": ch.get("group", ""),
                "is_live": True,
                "is_folder": False,
                "is_series": False
            })
        return items

    def search(self, query, page=1):
        """Searches live sports events."""
        events = self.get_items("special://events")
        q = query.lower().strip()
        return [i for i in events if q in i.get("title", "").lower()]

    def load(self, url):
        """Prepares playback options for Astra TV."""
        target_url = url
        title = "Live Stream"
        if url.startswith("{"):
            try:
                d = json.loads(url)
                target_url = d.get("url", url)
                title = d.get("title", "Live Stream")
            except Exception:
                pass

        return {
            "title": title,
            "options": [
                {
                    "label": f"[Live HD] Stream Direct ({title})",
                    "urls": [target_url]
                }
            ]
        }
