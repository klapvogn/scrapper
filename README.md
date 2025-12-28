# Universal Media Scraper - Windows Installation & Usage Guide

A Python-based scraper that downloads images and videos from Bunkr, Pixeldrain, Simpcity forums, and generic gallery sites.

## ⚠️ Important Legal Notice

**This tool is for educational purposes only.** Users are responsible for:
- Respecting copyright laws and intellectual property rights
- Complying with website Terms of Service
- Obtaining proper permissions before downloading content
- Using downloaded content legally and ethically

**The authors are not responsible for misuse of this tool.**

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [System Requirements](#-system-requirements)
- [Detailed Installation](#-detailed-installation)
- [Usage](#-usage)
- [Supported Sites](#-supported-sites)
- [Advanced Features](#-advanced-features)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)

---

## ✨ Features

- **Multi-site support**: Bunkr, Pixeldrain, Simpcity forums, viralthots.tv, and generic galleries
- **Automatic detection**: Detects site type and uses appropriate scraper
- **Bulk downloads**: Download entire albums, threads, or galleries
- **Smart filtering**: Removes thumbnails, avatars, and duplicate images
- **Resume support**: Skips already downloaded files
- **Video support**: Downloads videos from supported platforms
- **Forum pagination**: Handles multi-page forum threads
- **Cookie authentication**: Use browser cookies for logged-in access
- **Customizable filenames**: Add prefixes and organize downloads
- **Progress tracking**: Real-time download progress with file sizes

---

## 🚀 Quick Start (Windows)

**Get started in 5 minutes:**

1. **Install Python 3.8+** from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation

2. **Download files** to a folder (e.g., `C:\Scraper\`):
   - `universal_scraper.py`
   - `requirements.txt`

3. **Open Command Prompt** in that folder
   - Navigate to folder in File Explorer
   - Shift + Right-click → "Open PowerShell window here" or "Open command window here"

4. **Install dependencies:**
```cmd
   pip install -r requirements.txt
   playwright install chromium
```

5. **Run the script:**
```cmd
   python universal_scraper.py
```

6. **Follow the interactive prompts!** 🎉

---

## 💻 System Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (64-bit) |
| **Python** | 3.8 or higher |
| **RAM** | 4GB minimum, 8GB recommended |
| **Storage** | Varies (albums can be 10-50GB+) |
| **Internet** | Stable broadband connection |
| **Disk Space** | ~500MB for dependencies |

---

## 🔧 Detailed Installation

### Step 1: Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.x version (3.8 or higher)
3. Run the installer
4. **⚠️ IMPORTANT**: Check ✅ **"Add Python to PATH"** at the bottom
5. Click "Install Now"
6. Wait for installation to complete

**Verify Installation:**
```cmd
python --version
```
Should output something like: `Python 3.11.5`

If you get an error, restart Command Prompt or see [Troubleshooting](#troubleshooting).

---

### Step 2: Download Script Files

Create a folder for the scraper (e.g., `C:\Scraper\`) and download:

**1. universal_scraper.py** - The main script

**2. requirements.txt** - Create this file with the following content:
```txt
playwright>=1.40.0
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
tqdm>=4.66.0
aiofiles>=23.2.0
requests>=2.31.0
pillow>=10.0.0
```

**Your folder structure:**
```
C:\Scraper\
  ├── universal_scraper.py
  ├── requirements.txt
  └── downloads\ (will be created automatically)
```

---

### Step 3: Install Python Dependencies

Open Command Prompt in your scraper folder:

**Method 1: File Explorer**
1. Open the folder in File Explorer
2. Hold Shift + Right-click in empty space
3. Select "Open PowerShell window here" or "Open command window here"

**Method 2: Manual Navigation**
```cmd
cd C:\Scraper
```

**Install all required packages:**
```cmd
pip install -r requirements.txt
```

You should see packages being downloaded and installed:
```
Collecting playwright>=1.40.0
  Downloading playwright-x.x.x-py3-none-win_amd64.whl
...
Successfully installed playwright-x.x.x aiohttp-x.x.x ...
```

---

### Step 4: Install Playwright Browser

Playwright needs to download Chromium browser (~300MB):
```cmd
playwright install chromium
```

This will download and install the browser:
```
Downloading Chromium 120.0.6099.28 (playwright build v1091)
...
Chromium 120.0.6099.28 (playwright build v1091) downloaded to ...
```

**Installation Complete!** ✅

---

## 🚀 Usage

### Interactive Mode (Recommended for Beginners)

Simply run the script without arguments:
```cmd
python universal_scraper.py
```

You'll see:
```
======================================================================
UNIVERSAL SCRAPER
Supports: Bunkr, Pixeldrain, Simpcity Forums, Generic Galleries
======================================================================

Choose scraper mode:
1. Bunkr album/file
2. Pixeldrain album/file
3. Simpcity forum thread
4. Generic gallery (viralthots.tv, etc.)
5. Auto-detect from URL

Choose option (1/2/3/4/5):
```

Then enter your URL when prompted.

---

### Command Line Usage

For faster, repeatable downloads:

#### Basic Syntax
```cmd
python universal_scraper.py [URL] [OPTIONS]
```

#### Examples

**Bunkr Album:**
```cmd
python universal_scraper.py https://bunkr.site/a/ALBUM_ID
```

**Pixeldrain Album:**
```cmd
python universal_scraper.py https://pixeldrain.com/l/LIST_ID
```

**Pixeldrain with API Key:**
```cmd
python universal_scraper.py https://pixeldrain.com/l/LIST_ID -k YOUR_API_KEY
```

**Simpcity Forum Thread:**
```cmd
python universal_scraper.py https://simpcity.su/threads/thread-name.12345/
```

**Generic Gallery/Video:**
```cmd
python universal_scraper.py https://viralthots.tv/video/12345/
```

**Custom Output Directory:**
```cmd
python universal_scraper.py https://bunkr.site/a/xyz123 -o D:\My_Downloads
```

**Force Specific Mode:**
```cmd
python universal_scraper.py https://example.com/gallery --mode gallery
```

**Enable Debug Mode (for troubleshooting):**
```cmd
python universal_scraper.py https://simpcity.su/threads/name.123/ --mode forum --debug
```

---

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o DIR` | Output directory | `downloads` |
| `-r SECONDS` | Rate limit between requests | `5` |
| `-k KEY` | Pixeldrain API key | None |
| `--mode MODE` | Force mode: `auto`, `bunkr`, `pixeldrain`, `forum`, `gallery` | `auto` |
| `--debug` | Enable debug mode (saves HTML) | Off |

---

## 🌐 Supported Sites

### 1. Bunkr
**Supported URLs:**
- Albums: `https://bunkr.site/a/ALBUM_ID`
- Albums: `https://bunkr.cr/a/ALBUM_ID`
- Single files: `https://bunkr.*/f/FILE_ID`

**Features:**
- Multi-page album support
- Video downloads
- Automatic retry on 502/503 errors
- Network capture for dynamic URLs

**Notes:**
- Site domains change frequently (bunkr.site, bunkr.cr, bunkr.si, etc.)
- Large albums may take time due to rate limiting

---

### 2. Pixeldrain
**Supported URLs:**
- Albums/Lists: `https://pixeldrain.com/l/LIST_ID`
- Single files: `https://pixeldrain.com/u/FILE_ID`

**Features:**
- Fast API-based downloads
- Private file access with API key
- Direct download links

**Getting API Key (Optional):**
1. Sign up at pixeldrain.com
2. Go to: https://pixeldrain.com/user/api_keys
3. Create new API key
4. Use with `-k` parameter

**Example with API Key:**
```cmd
python universal_scraper.py https://pixeldrain.com/l/abc123 -k pd_api_xxxxxxxxxx
```

---

### 3. Simpcity Forums
**Supported URLs:**
- Threads: `https://simpcity.su/threads/NAME.ID/`
- Any page of a thread

**Features:**
- Multi-page thread support
- Smart image filtering
- Cookie-based authentication
- High-resolution image detection
- Removes thumbnails and avatars

**Requirements:**
- Cookie file for logged-in content (see [Forum Authentication](#forum-authentication))

---

### 4. Generic Galleries
**Supported Sites:**
- viralthots.tv
- Any gallery/album site with standard HTML

**Features:**
- Image and video detection
- iframe embed scraping
- Multiple resolution versions
- Video size filtering

---

## 🔐 Forum Authentication (Simpcity)

For forum threads requiring login, you need to export your browser cookies.

### Method 1: Browser Extension (Recommended)

**Chrome / Edge:**
1. Install [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)
2. Log into simpcity.su
3. Click the EditThisCookie icon
4. Click "Export" (bottom-left)
5. Copy the exported cookies
6. Create `forum_cookies.txt` in script folder
7. Paste cookies and save

**Firefox:**
1. Install [Cookie Quick Manager](https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/)
2. Log into simpcity.su
3. Open the extension
4. Search for "simpcity"
5. Select all cookies
6. Export as "Netscape" format
7. Save as `forum_cookies.txt` in script folder

---

### Method 2: Manual Cookie Export

**Chrome:**
1. Log into the forum
2. Press `F12` to open Developer Tools
3. Go to **Application** tab
4. Expand **Cookies** in left sidebar
5. Click on the forum domain
6. Find these cookies:
   - `xf_user`
   - `xf_session`
   - Any other session cookies
7. Create `forum_cookies.txt` in Netscape format (see example below)

**Netscape Cookie Format Example:**
```
# Netscape HTTP Cookie File
.simpcity.su    TRUE    /    FALSE    1735689600    xf_user    123456%2Cxxxxx
.simpcity.su    TRUE    /    FALSE    1735689600    xf_session    yyyyyyyyyyy
```

---

### Testing Cookies

Run the script with a forum URL to test:
```cmd
python universal_scraper.py https://simpcity.su/threads/test.123/
```

If cookies are valid, you'll see:
```
✓ Successfully accessed first page
```

If invalid:
```
✗ Login required or session expired!
```

**Cookie Troubleshooting:**
- Cookies expire after ~30 days - re-export regularly
- Make sure you're logged in before exporting
- Try logging out and back in before exporting
- Check file is named exactly `forum_cookies.txt`

---

## ⚙️ Advanced Features

### Multi-Page Thread Downloads

When scraping forum threads with multiple pages, you'll be prompted:
```
MULTI-PAGE THREAD DETECTED
This thread has 15 pages.

Download options:
1. Download from ALL pages
2. Download from current page only
3. Specify page range (e.g., 1-5 or 3,4,5)

Choose option (1/2/3):
```

**Examples:**
- `1` - Downloads all 15 pages
- `2` - Downloads only current page
- `3` then `1-5` - Downloads pages 1 through 5
- `3` then `1,3,5,7` - Downloads specific pages

---

### Smart Image Filtering

Forum scraper has two-phase filtering:

#### Phase 1: URL/Filename Filtering (Automatic)
Removes:
- Thumbnails (thumb_, _thumb, -thumb)
- Small sizes (96x96, 150x150, etc.)
- Avatars and icons
- Known CDN thumbnail patterns
- GIF files (optional)

#### Phase 2: Actual Property Checking (Optional)

Checks actual file properties:
- Minimum file size: 5KB
- Minimum dimensions: Both width/height > 100px
- Square icons: Squares ≤ 150px removed

**⚠️ Warning:** Phase 2 can be overly aggressive on CDN hosts.
```
Would you like to check actual image dimensions and file sizes?
⚠ WARNING: This can be overly aggressive and filter out valid images,
  especially on CDN hosts like jpg6.su.

1. Yes, check all images (may filter too many)
2. No, skip property checking (recommended for forums)

Choose option (1/2):
```

**Recommendation:** Choose `2` (skip) for forum downloads to avoid losing valid images.

---

### Filename Customization

Before downloading, you can customize filenames:
```
FILENAME SETTINGS
======================================================================

Suggested prefix: 'thread-name_'
Enter filename prefix (press Enter for 'thread-name_'):
```

**Examples:**
- Prefix `vacation_` → `vacation_001.jpg`, `vacation_002.jpg`
- Prefix `cat_photos_` → `cat_photos_001.jpg`, `cat_photos_002.jpg`
- No prefix (press Enter) → Uses original filenames

**Overwrite Options:**
```
Overwrite existing files?
(y)es, (n)o (skip), (a)uto-rename:
```

- `y` - Replace existing files
- `n` - Skip files that already exist
- `a` - Add `_1`, `_2`, etc. to duplicates (recommended)

---

### Video Filtering (Generic Galleries)

For sites with videos:
```
Small video filtering:
Small videos (< 1 MB) are often previews/thumbnails, not full videos.
Skip videos smaller than 1 MB? (y/n, default: y):
```

- `y` - Skip videos under 1MB (recommended)
- `n` - Download all videos
- Custom size: Enter `1.5` for 1.5MB minimum

---

### File Type Filtering (Forums)
```
File type filtering:
1. Download only JPG/JPEG/PNG files
2. Download all image types
3. Skip GIF files only

Choose option (1/2/3):
```

- `1` - Only static images (JPG/PNG)
- `2` - All image formats
- `3` - All except GIFs

---

## 🐛 Troubleshooting

### "Python is not recognized..."

**Error:**
```
'python' is not recognized as an internal or external command
```

**Solutions:**

**Option 1: Reinstall Python**
1. Uninstall Python from Windows Settings
2. Download from python.org
3. During install: ✅ Check "Add Python to PATH"
4. Restart Command Prompt

**Option 2: Manual PATH**
1. Find Python install location (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\`)
2. Windows Search → "Environment Variables"
3. Edit "Path" variable
4. Add Python folder and `Scripts` subfolder
5. Restart Command Prompt

**Option 3: Use Full Path**
```cmd
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe universal_scraper.py
```

**Verify:**
```cmd
python --version
```

---

### Module Not Found Errors

**Error:**
```
ModuleNotFoundError: No module named 'playwright'
```

**Solution:**

1. Ensure you're in the correct folder
2. Reinstall dependencies:
```cmd
   pip install -r requirements.txt
```

3. If still failing, try upgrading pip first:
```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
```

4. For Playwright specifically:
```cmd
   pip install playwright
   playwright install chromium
```

---

### HTTP 502/503 Server Errors (Bunkr)

**Error:**
```
⚠ HTTP 502 - Server temporarily unavailable
```

**What it means:** Bunkr's servers are overloaded or down.

**Solutions:**
- Script auto-retries with exponential backoff (1s, 2s, 4s, 8s, 16s)
- Wait 5-10 minutes and try again
- Try during off-peak hours (early morning)
- Check if bunkr is down: https://downforeveryoneorjustme.com/bunkr.site

**Not a bug** - Server-side issue, script handles it automatically.

---

### Cookie Authentication Failed

**Error:**
```
✗ Login required or session expired!
```

**Solutions:**

1. **Re-export fresh cookies:**
   - Log out of forum
   - Clear browser cookies for site
   - Log back in
   - Export new cookies

2. **Check cookie file:**
   - Named exactly `forum_cookies.txt`
   - In same folder as script
   - Not empty
   - Not corrupted

3. **Verify cookie format:**
   - Must be Netscape format
   - Check for proper formatting
   - No extra blank lines at top

4. **Test cookies:**
```cmd
   python universal_scraper.py --mode forum
```
   Enter any forum URL to test

5. **Check expiration:**
   - Cookies expire (usually 30 days)
   - Look for expiration timestamps in file
   - Re-export if expired

---

### No Images Found (Forums)

**Possible Causes:**
1. Filtering too aggressive
2. Content behind login (invalid cookies)
3. Different HTML structure
4. Thread has no images

**Solutions:**

**1. Enable Debug Mode:**
```cmd
python universal_scraper.py URL --mode forum --debug
```
- Check `downloads/debug_html/` folder
- Open `page_1.html` in browser
- Verify images are visible

**2. Skip Property Checking:**
- When prompted for Phase 2 filtering, choose `2` (skip)
- This prevents false positives

**3. Check Cookies:**
- Re-export cookies
- Verify you can see content in browser when logged in

**4. Try Different URL:**
- Some forum sections may have different structure
- Test with known working thread first

---

### Download Fails at 0 Bytes

**Error:**
```
✗ Downloaded 0 bytes
```

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| **File deleted from server** | Nothing you can do - file is gone |
| **Access token expired** | Re-run for token-based URLs |
| **Rate limiting** | Script auto-handles, wait a moment |
| **Network issue** | Check internet connection |
| **Region blocked** | Try with VPN |
| **Wrong URL** | Verify URL is correct |

---

### Playwright Browser Issues

**Error:**
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Solution:**
```cmd
playwright install --force chromium
```

**If that fails:**
```cmd
pip uninstall playwright
pip install playwright
playwright install chromium
```

---

### Permission Denied / Access Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

1. **Close files:** Make sure no files in output folder are open
2. **Run as Administrator:** Right-click Command Prompt → "Run as Administrator"
3. **Check antivirus:** May be blocking script, add to whitelist
4. **Choose different output folder:** Use `-o C:\Temp\downloads`

---

### Slow Downloads

**Why downloads are slow:**
- **Rate limiting** prevents IP bans (default 5 seconds)
- **Server speed** varies by host
- **Large files** (videos) take time
- **Network speed** limitation

**Speed up (use carefully):**
```cmd
python universal_scraper.py URL -r 2
```
- Lower rate limit (2 seconds instead of 5)
- ⚠️ Risk of temporary IP ban
- Recommended: 3-5 seconds

**Note:** Respect servers - aggressive scraping can lead to blocks.

---

## 📊 Understanding Output

### Console Output Symbols

| Symbol | Meaning | Example |
|--------|---------|---------|
| `→` | In progress | `→ Opening in browser...` |
| `✓` | Success | `✓ Saved (2.45 MB)` |
| `✗` | Failed | `✗ HTTP 404` |
| `⊙` | Skipped | `⊙ File exists: image.jpg` |
| `⚠` | Warning | `⚠ File small, may not be valid` |
| `ℹ` | Info | `ℹ No Pixeldrain API key` |
| `⏳` | Waiting | `⏳ Waiting 2s before retry...` |
| `📁` | Album/folder | `📁 Scraping Bunkr album` |
| `🔑` | Authentication | `🔑 Using Pixeldrain API key` |

---

### Progress Examples

**Bunkr Download:**
```
[5/20] https://bunkr.site/f/abc123
    → File: vacation_photo.jpg
    → Reinforced URL: https://get.bunkrr.su/file/xyz
    → Opening in browser: https://get.bunkrr.su/file/xyz
    → Captured: https://cdn.bunkr.ru/vacation_photo.jpg
    ↓ vacation_photo.jpg 100%|████████| 2.45M/2.45M [00:03<00:00]
    ✓ vacation_photo.jpg (2.45 MB)
```

**Forum Download:**
```
[12/50] Downloading: photo_012.jpg
  → Trying URL 1/1
  ✓ Saved (1.2 MB)
```

**Failed Download:**
```
[8/20] Downloading: video_008.mp4
  ✗ Failed: 404 Not Found
     → Likely: File not found or URL expired
```

---

### Download Summary

At the end, you'll see a summary:
```
======================================================================
DOWNLOAD SUMMARY
======================================================================
Pages processed: 3
Total URLs found: 150
Filtered by URL/filename: 45
Filtered by size/dimensions: 12
Filtered by file type: 5
Successfully downloaded: 75
Skipped (already existed): 10
Failed: 3
Location: C:\Scraper\downloads\thread-name_20241228_143022
```

---

### File Organization
```
downloads/
  ├── album_name_20241228_143022/
  │   ├── image_001.jpg (2.3 MB)
  │   ├── image_002.png (1.8 MB)
  │   ├── video_003.mp4 (45.2 MB)
  │   └── image_004.jpg (3.1 MB)
  │
  ├── thread_name_20241228_150000/
  │   ├── photo_001.jpg
  │   ├── photo_002.jpg
  │   └── failed_urls.txt  (if any downloads failed)
  │
  └── debug_html/ (only in debug mode)
      ├── page_1.html
      └── page_2.html
```

**Timestamp format:** `YYYYMMDD_HHMMSS`
- Makes folders unique
- Easy to sort chronologically
- Safe for batch downloads

---

## 💡 Best Practices

### 1. Start Small
Test with 1-2 images before downloading entire albums:
```cmd
# Try one file first
python universal_scraper.py https://bunkr.site/f/single-file
```

### 2. Use Appropriate Rate Limiting
**Recommended values:**
- **Bunkr:** 5 seconds (default)
- **Pixeldrain:** 2 seconds
- **Forums:** 1-2 seconds
- **Galleries:** 1 second
```cmd
python universal_scraper.py URL -r 5
```

### 3. Organize Your Downloads
Create separate folders for different sources:
```cmd
python universal_scraper.py URL -o D:\Downloads\Bunkr
python universal_scraper.py URL -o D:\Downloads\Forums
```

### 4. Monitor Disk Space
Large albums can be 10-50GB+:
- Check available space before starting
- Use external drive for large collections
- Clean up failed/partial downloads

### 5. Keep Python Updated
```cmd
python --version
```
Update every 3-6 months from python.org

### 6. Maintain Fresh Cookies
For forum scraping:
- Re-export cookies monthly
- After changing password
- If downloads start failing

### 7. Handle Failures Gracefully
- Read error messages carefully
- Check failed_urls.txt for troubleshooting
- Re-run script for failed downloads (skips existing)

### 8. Respect Rate Limits
- Don't set `-r` below 1 second
- Excessive requests may trigger IP bans
- Patience prevents problems

### 9. Use Stable Internet
- Pause other downloads during scraping
- Avoid Wi-Fi if possible (use ethernet)
- Consider download manager for very large files

### 10. Backup Your Setup
Keep copies of:
- `universal_scraper.py`
- `requirements.txt`
- `forum_cookies.txt`
- Working configuration

---

## 🔄 Updating the Script

### Updating Script Files

1. **Backup current version:**
```cmd
   copy universal_scraper.py universal_scraper_backup.py
```

2. **Download new version** and replace

3. **Update dependencies:**
```cmd
   pip install -r requirements.txt --upgrade
```

### Updating Individual Packages
```cmd
pip install --upgrade playwright aiohttp beautifulsoup4 tqdm aiofiles requests pillow
```

### Checking for Updates
```cmd
pip list --outdated
```

Shows packages that can be updated.

---

## 📝 Batch Downloads (Multiple URLs)

### Create a Batch File

**download_multiple.bat:**
```batch
@echo off
echo ========================================
echo Universal Scraper - Batch Downloader
echo ========================================
echo.

echo [1/3] Downloading Bunkr Album 1...
python universal_scraper.py "https://bunkr.site/a/album1" -o "Downloads/Bunkr/Album1"
echo.

echo [2/3] Downloading Bunkr Album 2...
python universal_scraper.py "https://bunkr.site/a/album2" -o "Downloads/Bunkr/Album2"
echo.

echo [3/3] Downloading Pixeldrain List...
python universal_scraper.py "https://pixeldrain.com/l/list123" -o "Downloads/Pixeldrain" -k YOUR_API_KEY
echo.

echo ========================================
echo All downloads complete!
echo ========================================
pause
```

**Save as** `download_multiple.bat` in script folder, then double-click to run.

---

### URL List File

**urls.txt:**
```
https://bunkr.site/a/album1
https://bunkr.site/a/album2
https://pixeldrain.com/l/list123
https://simpcity.su/threads/thread1.123/
```

**download_from_list.bat:**
```batch
@echo off
for /f "tokens=*" %%i in (urls.txt) do (
    echo Downloading: %%i
    python universal_scraper.py "%%i"
    echo.
)
pause
```

---

## ❓ FAQ

### General Questions

**Q: Is this tool legal to use?**  
A: The tool itself is legal. However, YOU are responsible for:
- Following copyright laws
- Respecting site Terms of Service
- Not downloading copyrighted content without permission
- Using downloaded content legally

**Q: Does this work on Mac or Linux?**  
A: Yes, but this guide is Windows-specific. For Mac/Linux:
- Use `python3` instead of `python`
- Use `/` instead of `\` for paths
- Installation steps are similar

**Q: Is my data safe?**  
A: Yes. The script:
- Runs entirely locally on your computer
- Makes no external connections except to download files
- Stores no data about you
- Does not phone home

**Q: Can I pause and resume downloads?**  
A: Yes! Re-run the same command. The script skips files that already exist.

---

### Performance Questions

**Q: Why is it so slow?**  
A: Rate limiting prevents IP bans. To speed up (carefully):
```cmd
python universal_scraper.py URL -r 2
```
Lower values = faster but riskier. Don't go below 1.

**Q: Can I download multiple albums simultaneously?**  
A: Not recommended. Run them sequentially:
- Prevents confusion
- Avoids rate limiting issues
- Better error handling

**Q: How long does a typical album take?**  
A: Depends on:
- Number of files: 100 files ≈ 10-20 minutes
- File sizes: Videos much slower than images
- Rate limiting: Default 5s = 12 files/minute max
- Server speed: Varies by host

---

### Technical Questions

**Q: Where are files downloaded to?**  
A: By default: `downloads/` folder in script directory.
- Custom location: `-o C:\Your\Path`
- Each download gets timestamped subfolder

**Q: What if a file already exists?**  
A: Script will ask:
- **(y)es** - Overwrite
- **(n)o** - Skip
- **(a)uto-rename** - Add _1, _2, etc.

**Q: Can I download from multiple sites at once?**  
A: Yes, but use separate command prompts:
```cmd
# Window 1
python universal_scraper.py https://bunkr.site/a/album1

# Window 2
python universal_scraper.py https://pixeldrain.com/l/list1
```

**Q: Does this support proxies or VPN?**  
A: Not built-in. Use system-wide VPN if needed.

**Q: What video formats are supported?**  
A: MP4, WebM, MOV, AVI, MKV

---

### Pixeldrain Questions

**Q: Do I need a Pixeldrain API key?**  
A: No, for public files. Yes, for:
- Private files
- Faster downloads
- Higher rate limits
- Premium content

**Q: How do I get a Pixeldrain API key?**  
A:
1. Sign up at pixeldrain.com
2. Go to https://pixeldrain.com/user/api_keys
3. Create new API key
4. Copy the key (starts with `pd_api_`)

**Q: How do I use the API key?**  
A:
```cmd
python universal_scraper.py https://pixeldrain.com/l/abc123 -k pd_api_xxxxxx
```

---

### Forum Questions

**Q: Why do I need cookies for forums?**  
A: Many forum threads require login to view. Cookies authenticate you.

**Q: Are my credentials stored?**  
A: No. Only session cookies are stored locally. Your password is never saved.

**Q: How often do I need to re-export cookies?**  
A: Every 30 days typically, or:
- After changing password
- If downloads start failing
- After clearing browser cookies

**Q: Can I share my cookies?**  
A: **NO!** Cookies contain your login session. Sharing them = sharing your account.

**Q: What if I don't want to use cookies?**  
A: You can only download from public threads/posts that don't require login.

---

### Filtering Questions

**Q: Why are some images skipped?**  
A: Smart filtering removes:
- Thumbnails and avatars
- Very small images (< 5KB)
- Tiny dimensions (< 100px)
- Known icon sizes (96x96, etc.)
- GIFs (optional)

**Q: How do I disable filtering?**  
A: When prompted for "Phase 2: Actual image properties", choose option `2` (skip).

**Q: Can I download thumbnails too?**  
A: Not currently. The script is designed to get full-size images only.

**Q: Why are valid images being filtered?**  
A: Phase 2 can be overly aggressive. Choose to skip it:
```
Choose option (1/2): 2
```

---

### Error Questions

**Q: What does "HTTP 404" mean?**  
A: File not found. Possible causes:
- File was deleted from server
- URL is incorrect
- Link expired

**Q: What does "HTTP 403" mean?**  
A: Access forbidden. Possible causes:
- Need authentication (cookies)
- IP blocked
- Access token expired

**Q: What does "HTTP 502/503" mean?**  
A: Server temporarily down/overloaded. Script auto-retries. Just wait.

**Q: What if downloads keep failing?**  
A:
1. Check internet connection
2. Try with VPN
3. Wait 10 minutes and retry
4. Check if site is down
5. Enable `--debug` mode and check logs

---

## 🛡️ Privacy & Security

### Data Collection
- ✅ **No telemetry** - Script sends no data to developers
- ✅ **No tracking** - No analytics or usage statistics
- ✅ **No accounts** - No registration required
- ✅ **Fully local** - Runs entirely on your computer

### What Gets Stored Locally
- Downloaded files (obviously)
- Cookie file (if using forum mode)
- Debug HTML (if debug enabled)
- Failed URLs log (if downloads fail)

### Security Best Practices
1. **Keep cookies private** - Never share `forum_cookies.txt`
2. **Don't share API keys** - Your Pixeldrain API key is personal
3. **Use HTTPS only** - Script enforces secure connections
4. **Update regularly** - Keep Python and packages updated
5. **Scan downloads** - Run antivirus on downloaded files
6. **Secure your system** - Use password-protected user account

### Cookie Security
Your `forum_cookies.txt` file contains:
- Session tokens (login state)
- **NOT passwords** (those are never stored)

If compromised:
1. Delete `forum_cookies.txt`
2. Log out of forum in browser
3. Change your forum password
4. Log back in and re-export fresh cookies

---

## 📞 Getting Help

### Self-Help Steps

1. **Read this guide** - Most issues covered here
2. **Check error message** - Often tells you exactly what's wrong
3. **Enable debug mode** - Get detailed logs
```cmd
   python universal_scraper.py URL --debug
```
4. **Try with simple URL** - Test with single file first
5. **Update everything** - Latest Python, latest packages
6. **Restart** - Computer, command prompt, browser

### Debug Mode

Enable detailed logging:
```cmd
python universal_scraper.py URL --mode forum --debug
```

Creates:
- `downloads/debug_html/` folder
- Detailed console output
- `failed_urls.txt` with error details

---

## 🏁 Final Tips

### For Best Results:

1. ✅ **Test first** - Try 1-2 files before bulk downloads
2. ✅ **Use defaults** - Don't change rate limits unless necessary
3. ✅ **Stay updated** - Update monthly with `pip install -r requirements.txt --upgrade`
4. ✅ **Read errors** - Error messages are helpful, not cryptic
5. ✅ **Be patient** - Large downloads take time
6. ✅ **Organize** - Use custom output folders
7. ✅ **Monitor space** - Check disk space regularly
8. ✅ **Respect servers** - Don't hammer with requests
9. ✅ **Keep backups** - Of your script and config
10. ✅ **Stay legal** - Respect copyright and ToS

---

## 📜 License & Disclaimer

**USE AT YOUR OWN RISK**

This tool is provided **as-is** with **no warranties**. Users are **solely responsible** for:

✓ Compliance with all applicable laws  
✓ Respecting copyright and intellectual property  
✓ Adhering to website Terms of Service  
✓ Obtaining necessary permissions before downloading  
✓ Any legal, financial, or other consequences of misuse  

The authors:
- Do NOT endorse illegal downloading
- Do NOT encourage copyright violation
- Do NOT provide support for illegal activities
- Assume NO liability for how you use this tool

**By using this script, you agree to these terms.**

---

## 📚 Additional Resources

- [Python Official Documentation](https://docs.python.org/)
- [Playwright Documentation](https://playwright.dev/python/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests Documentation](https://requests.readthedocs.io/)

---

**Version**: 2.0  
**Last Updated**: December 2024  
**Python Version**: 3.8+  
**Tested On**: Windows 10/11 64-bit  
**License**: Educational Use Only

---

**Happy downloading! 🎉**


*Remember: With great power comes great responsibility. Use wisely.*



