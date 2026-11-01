# Astra TV Extensions & Scrapers Repository 🚀

Official Cloudstream-style Scraper Repository for **Astra TV**.  
Replicates Phisher98's repository architecture for Kodi.

---

## 📦 Repository Details

* **Repository Manifest URL**:  
  `https://raw.githubusercontent.com/Dangerous-Taabar/astra-tv-extensions/main/repo.json`
* **Shortcode**: `astra`

---

## 📺 Available Scrapers

| Scraper | Categories / Types | Language | Status |
| :--- | :--- | :--- | :--- |
| **HDhub4u** | Movies, Web Series, Anime (4K, 1080p BluRay, WEB-DL, HEVC) | Hindi, Multi | ✅ Active |
| **DesiSerials** | TV Serials (Star Plus, Zee TV, Sony, Colors, SAB TV, etc.) | Hindi | ✅ Active |
| **AnimeDubHindi** | Anime Movies, Anime Series, Donghua (Hindi, Tamil, Telugu Dubbed) | Hindi, Multi | ✅ Active |

---

## 🛠️ How to Add a New Scraper (Up to 40+ Scrapers)

Adding a new scraper takes just 2 simple steps:

1. **Add Scraper File**:
   Put your new provider file (e.g. `vegamovies.py`, `bollyflix.py`, `filmyzilla.py`) inside the `providers/` folder:
   ```python
   class VegaMoviesProvider:
       name = "VegaMovies"
       lang = "hi"
       supported_types = ["Movie", "TvSeries"]
       ...
   ```

2. **Run Manifest Builder**:
   ```bash
   python make_manifest.py
   ```
   This automatically reads all files in `providers/`, extracts metadata, and updates `plugins.json` and `repo.json`!

3. **Push to GitHub**:
   In VS Code Source Control, or via terminal:
   ```bash
   git add .
   git commit -m "Add new scraper"
   git push
   ```

---

## 📥 Installation in Astra TV

1. Open **Astra TV** inside Kodi.
2. Go to **Settings > Repositories > Add Repository URL**.
3. Paste:
   `https://raw.githubusercontent.com/Dangerous-Taabar/astra-tv-extensions/main/repo.json`
   *(or use shortcode `astra` once configured)*
4. Click on the repository and click **Install** on any scraper you want!
