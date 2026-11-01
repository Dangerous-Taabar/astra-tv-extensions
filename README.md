# Astra TV Extensions & Scrapers Repository 🚀

Official Scraper & Extension Repository for **Astra TV**.  
Features secure `.atx` (Astra TV Extension) packages with SHA-256 integrity verification, mirroring Cloudstream's `.cs3` architecture.

---

## 📦 Repository Details

* **Repository Manifest URL**:  
  `https://raw.githubusercontent.com/Dangerous-Taabar/astra-tv-extensions/main/repo.json`
* **Shortcode**: `astra` or `astratv`

---

## 📺 Available Extensions (.atx)

| Extension | Package | Categories / Types | Language | Status |
| :--- | :--- | :--- | :--- | :--- |
| **HDhub4u** | `HDhub4u.atx` | Movies, Web Series (4K, 1080p, HEVC) | Hindi, Multi | ✅ Active |
| **DesiSerials** | `DesiSerials.atx` | TV Serials (Star Plus, Zee TV, Sony, Colors, SAB TV) | Hindi | ✅ Active |
| **AnimeDubHindi** | `AnimeDubHindi.atx` | Anime Movies & Series (Hindi, Tamil, Telugu Dubbed) | Hindi, Multi | ✅ Active |
| **Cricfy** | `Cricfy.atx` | Live Sports & Cricket (TATA Play, Hotstar, FanCode) | English, Hindi | ✅ Active |
| **LivXow** | `LivXow.atx` | Live Sports Events & TV Channels (TNT, Prime, Willow) | English, Multi | ✅ Active |

---

## 🛠️ How to Add a New Extension (.atx)

1. **Add Scraper File**:
   Add your scraper file (e.g. `vegamovies.py`) inside `providers/`:
   ```python
   class VegaMoviesProvider:
       name = "VegaMovies"
       lang = "hi"
       supported_types = ["Movie", "TvSeries"]
       ...
   ```

2. **Run .atx Builder**:
   ```bash
   python make_manifest.py
   ```
   This automatically:
   - Compiles and packages your provider into `builds/<Name>.atx` with an embedded manifest.
   - Calculates the exact file size and cryptographic SHA-256 checksum.
   - Updates `plugins.json` and `repo.json`.

3. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Add new extension"
   git push
   ```

---

## 📥 Installation in Astra TV

1. Open **Astra TV** in Kodi.
2. Go to **Settings > Repositories > Add Repository URL** (or use shortcode `astra`).
3. Click on **Astra TV Extensions**.
4. Click **Install** on any provider to download and install its `.atx` package!
