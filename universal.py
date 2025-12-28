#!/usr/bin/env python3
"""
Universal Scraper for Bunkr, Pixeldrain, and Simpcity Forums, viralthots.tv
Requires: pip install playwright aiohttp beautifulsoup4 tqdm aiofiles requests pillow
          playwright install chromium
"""
import asyncio
import os
import re
import base64
import time
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Optional
from http.cookiejar import MozillaCookieJar
from io import BytesIO

# Async imports
import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm
import aiofiles
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Sync imports for forum scraper
import requests
from PIL import Image


class UniversalScraper:
    def __init__(self, output_dir: str = "downloads", rate_limit: int = 5, pixeldrain_api_key: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.downloaded_files = set()
        self.playwright = None
        self.browser = None
        self.context = None
        self.pixeldrain_api_key = pixeldrain_api_key
        
        # Load API key from environment if not provided
        if not self.pixeldrain_api_key:
            self.pixeldrain_api_key = os.getenv('PIXELDRAIN_API_KEY')
        
        if self.pixeldrain_api_key:
            print(f"🔑 Using Pixeldrain API key: {self.pixeldrain_api_key[:8]}...")
        else:
            print("ℹ️  No Pixeldrain API key (public access only)")
        
    async def init_browser(self):
        """Initialize Playwright browser"""
        if self.browser:
            return
            
        print("🌐 Starting browser...")
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-popup-blocking'
            ]
        )
        
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
    async def close_browser(self):
        """Safely close browser"""
        try:
            if self.context:
                await self.context.close()
        except:
            pass
            
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
            
        try:
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    def get_pixeldrain_headers(self) -> dict:
        """Get headers with API key authentication for Pixeldrain"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        if self.pixeldrain_api_key:
            # Pixeldrain uses Basic auth with api_key as username and empty password
            auth_string = f"{self.pixeldrain_api_key}:"
            encoded = base64.b64encode(auth_string.encode()).decode()
            headers['Authorization'] = f'Basic {encoded}'
        
        return headers
    
    async def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch HTML page"""
        async with aiohttp.ClientSession() as session:
            await asyncio.sleep(0.2)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                html = await response.text()
                return BeautifulSoup(html, 'html.parser')
    
    async def download_file(self, url: str, filepath: Path, desc: str = ""):
        """Download file with retries"""
        if filepath.exists() and filepath.stat().st_size > 0:
            print(f"    ⊙ File exists: {filepath.name}")
            return True
            
        retries = 5  # Increased retries for 502 errors
        for attempt in range(retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://bunkr.cr/'
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=300)) as response:
                        if response.status == 502 or response.status == 503:
                            print(f"    ⚠ HTTP {response.status} - Server temporarily unavailable")
                            if attempt < retries - 1:
                                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8, 16 seconds
                                print(f"    ⏳ Waiting {wait_time}s before retry...")
                                await asyncio.sleep(wait_time)
                                continue
                            return False
                        
                        if response.status != 200:
                            print(f"    ✗ HTTP {response.status}")
                            if attempt < retries - 1 and response.status >= 500:
                                await asyncio.sleep(2)
                                continue
                            return False
                        
                        # Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        if 'text/html' in content_type:
                            print(f"    ✗ Got HTML instead of file")
                            return False
                        
                        total_size = int(response.headers.get('content-length', 0))
                        
                        pbar = tqdm(
                            total=total_size if total_size > 0 else None,
                            unit='B',
                            unit_scale=True,
                            desc=f"    ↓ {filepath.name[:50]}",
                            leave=False
                        )
                        
                        bytes_downloaded = 0
                        async with aiofiles.open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                bytes_downloaded += len(chunk)
                                pbar.update(len(chunk))
                        
                        pbar.close()
                        
                        if bytes_downloaded == 0:
                            print(f"    ✗ Downloaded 0 bytes")
                            if filepath.exists():
                                filepath.unlink()
                            return False
                        
                        print(f"    ✓ {filepath.name} ({bytes_downloaded / 1024 / 1024:.2f} MB)")
                        return True
                        
            except asyncio.TimeoutError:
                print(f"    ✗ Timeout (attempt {attempt+1}/{retries})")
                if filepath.exists():
                    filepath.unlink()
                if attempt < retries - 1:
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"    ✗ Download error (attempt {attempt+1}/{retries}): {e}")
                if filepath.exists():
                    filepath.unlink()
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    
        return False
    
    async def download_file_pixeldrain(self, url: str, filepath: Path, desc: str = ""):
        """Download file from Pixeldrain with authentication"""
        if filepath.exists() and filepath.stat().st_size > 0:
            print(f"    ⊙ File exists: {filepath.name}")
            return True
            
        retries = 3
        for attempt in range(retries):
            try:
                headers = self.get_pixeldrain_headers()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=300)) as response:
                        if response.status != 200:
                            print(f"    ✗ HTTP {response.status}")
                            if attempt < retries - 1:
                                await asyncio.sleep(2)
                                continue
                            return False
                        
                        # Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        if 'text/html' in content_type:
                            print(f"    ✗ Got HTML instead of file")
                            return False
                        
                        total_size = int(response.headers.get('content-length', 0))
                        
                        pbar = tqdm(
                            total=total_size if total_size > 0 else None,
                            unit='B',
                            unit_scale=True,
                            desc=f"    ↓ {filepath.name[:50]}",
                            leave=False
                        )
                        
                        bytes_downloaded = 0
                        async with aiofiles.open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                bytes_downloaded += len(chunk)
                                pbar.update(len(chunk))
                        
                        pbar.close()
                        
                        if bytes_downloaded == 0:
                            print(f"    ✗ Downloaded 0 bytes")
                            if filepath.exists():
                                filepath.unlink()
                            return False
                        
                        print(f"    ✓ {filepath.name} ({bytes_downloaded / 1024 / 1024:.2f} MB)")
                        return True
                        
            except Exception as e:
                print(f"    ✗ Download error (attempt {attempt+1}/{retries}): {e}")
                if filepath.exists():
                    filepath.unlink()
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    
        return False
    
    # ============ PIXELDRAIN METHODS ============
    
    async def scrape_pixeldrain_file(self, file_id: str, output_dir: Path, filename: str = None):
        """Download a single file from Pixeldrain"""
        try:
            # Pixeldrain direct download URL
            download_url = f"https://pixeldrain.com/api/file/{file_id}"
            
            # Get filename if not provided
            if not filename:
                info_url = f"https://pixeldrain.com/api/file/{file_id}/info"
                headers = self.get_pixeldrain_headers()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(info_url, headers=headers) as response:
                        if response.status == 200:
                            info = await response.json()
                            filename = info.get('name', f"{file_id}.bin")
                        else:
                            filename = f"{file_id}.bin"
            
            # Sanitize filename
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            
            print(f"    → File: {filename}")
            print(f"    → Download URL: {download_url}")
            
            filepath = output_dir / filename
            
            # Download with authentication
            success = await self.download_file_pixeldrain(download_url, filepath, filename)
            return success
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return False
    
    async def scrape_pixeldrain_list(self, list_id: str):
        """Scrape a Pixeldrain list/album"""
        print(f"📁 Scraping Pixeldrain list: https://pixeldrain.com/l/{list_id}")
        
        # Get list info via API
        api_url = f"https://pixeldrain.com/api/list/{list_id}"
        headers = self.get_pixeldrain_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status != 200:
                        print(f"✗ Failed to get list info: HTTP {response.status}")
                        return
                    
                    data = await response.json()
                    
                    list_title = data.get('title', list_id)
                    files = data.get('files', [])
                    
                    print(f"Album: {list_title}")
                    print(f"Found {len(files)} files\n")
                    
                    # Sanitize album name
                    album_name = re.sub(r'[<>:"/\\|?*]', '', list_title)
                    album_dir = self.output_dir / album_name
                    album_dir.mkdir(parents=True, exist_ok=True)
                    
                    success_count = 0
                    fail_count = 0
                    
                    # Download each file
                    for idx, file_info in enumerate(files, 1):
                        file_id = file_info.get('id')
                        filename = file_info.get('name', f"{file_id}.bin")
                        
                        print(f"[{idx}/{len(files)}] {filename}")
                        
                        success = await self.scrape_pixeldrain_file(file_id, album_dir, filename)
                        
                        if success:
                            success_count += 1
                        else:
                            fail_count += 1
                        
                        print()
                        
                        # Rate limiting
                        if idx < len(files):
                            await asyncio.sleep(0.5)
                    
                    print(f"\n{'='*60}")
                    print(f"✓ Album complete: {album_dir}")
                    print(f"✓ Successfully downloaded: {success_count}/{len(files)}")
                    print(f"✗ Failed: {fail_count}/{len(files)}")
                    print(f"{'='*60}")
                    
        except Exception as e:
            print(f"✗ Error scraping Pixeldrain list: {e}")
            import traceback
            traceback.print_exc()
    
    # ============ BUNKR METHODS ============
    
    async def get_download_url_with_network_capture(self, url: str) -> Optional[list]:
        """Capture actual download URL by monitoring network requests - returns list of URLs to try"""
        if not self.context:
            await self.init_browser()
            
        page = None
        try:
            print(f"    → Opening in browser: {url}")
            page = await self.context.new_page()
            
            download_urls = []
            
            async def capture_request(request):
                req_url = request.url
                if any(pattern in req_url.lower() for pattern in [
                    '.mp4', '.jpg', '.jpeg', '.png', '.gif', '.webp', 
                    '.mkv', '.avi', '.mov', 'cdn', 'stream', 'media'
                ]):
                    if not any(bad in req_url.lower() for bad in [
                        'porn', 'xxx', 'ads', 'analytics', 'tracker', 'popup', 'imcdn.pro'
                    ]):
                        download_urls.append(req_url)
                        print(f"    → Captured: {req_url[:80]}...")
            
            page.on('request', capture_request)
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            except PlaywrightTimeout:
                print(f"    ⚠ Page load timeout (continuing anyway)")
            
            await asyncio.sleep(2)
            
            try:
                await page.evaluate('''() => {
                    document.querySelectorAll('iframe').forEach(f => f.remove());
                }''')
                await asyncio.sleep(0.5)
            except:
                pass
            
            try:
                selectors = ['a#download-btn', 'a[data-id]', 'a.btn-main', 'a[href*="download"]']
                for selector in selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn:
                            print(f"    → Clicking: {selector}")
                            await btn.evaluate('el => el.click()')
                            await asyncio.sleep(3)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"    ⚠ Click error: {e}")
            
            final_url = page.url
            if final_url != url and 'get.bunkrr.su' not in final_url:
                if any(ext in final_url.lower() for ext in ['.mp4', '.jpg', '.png', '.gif']):
                    download_urls.append(final_url)
                    print(f"    → Page redirected to: {final_url[:80]}...")
            
            await page.close()
            
            if not download_urls:
                print(f"    ✗ No download URL captured")
                return None
            
            # Prioritize URLs
            prioritized = []
            
            # First pass: bunkr.ru domains
            for url in download_urls:
                if 'bunkr.ru' in url.lower() or 'bunkr.si' in url.lower() or 'bunkr.la' in url.lower():
                    if any(ext in url.lower() for ext in ['.mp4', '.jpg', '.png', '.gif', '.webm', '.jpeg']):
                        prioritized.append(url)
            
            # Second pass: other domains with file extensions (except cache8.st)
            for url in download_urls:
                if url not in prioritized:
                    if 'cache8.st' not in url.lower():
                        if any(ext in url.lower() for ext in ['.mp4', '.jpg', '.png', '.gif', '.webm', '.jpeg']):
                            prioritized.append(url)
            
            # Third pass: cache8.st as last resort
            for url in download_urls:
                if url not in prioritized:
                    if any(ext in url.lower() for ext in ['.mp4', '.jpg', '.png', '.gif', '.webm', '.jpeg']):
                        prioritized.append(url)
            
            if prioritized:
                print(f"    → Found {len(prioritized)} download URL(s)")
                await asyncio.sleep(1)
                return prioritized
            
            return download_urls if download_urls else None
            
        except Exception as e:
            print(f"    ✗ Browser error: {e}")
            if page:
                try:
                    await page.close()
                except:
                    pass
            return None
    
    async def scrape_bunkr_file(self, url: str, output_dir: Path):
        """Scrape a single file from Bunkr"""
        try:
            soup = await self.fetch_page(url)
            
            filename = None
            h1 = soup.select_one('h1')
            if h1:
                filename = h1.get_text().strip()
            
            if not filename or '.' not in filename:
                filename = f"{url.split('/')[-1]}.mp4"
            
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            print(f"    → File: {filename}")
            
            download_btn = soup.select_one('a.btn-main[href*="get.bunkr"]')
            if not download_btn:
                download_btn = soup.select_one('a#download-btn')
            
            if not download_btn:
                print(f"    ✗ No download button found")
                return False
            
            reinforced_url = download_btn.get('href')
            if reinforced_url and reinforced_url.startswith('/'):
                parsed = urlparse(url)
                reinforced_url = f"{parsed.scheme}://{parsed.netloc}{reinforced_url}"
            
            if not reinforced_url or reinforced_url == '#':
                data_id = download_btn.get('data-id')
                if data_id:
                    reinforced_url = f"https://get.bunkrr.su/file/{data_id}"
                else:
                    print(f"    ✗ No valid download URL found")
                    return False
            
            print(f"    → Reinforced URL: {reinforced_url}")
            
            # Get list of download URLs to try
            download_urls = await self.get_download_url_with_network_capture(reinforced_url)
            
            if not download_urls:
                print(f"    ✗ Could not resolve download URL")
                return False
            
            filepath = output_dir / filename
            
            # Try each URL in order until one works
            for idx, download_url in enumerate(download_urls, 1):
                if len(download_urls) > 1:
                    print(f"    → Trying URL {idx}/{len(download_urls)}")
                
                success = await self.download_file(download_url, filepath, filename)
                
                if success:
                    return True
                
                # If not last URL, wait a bit before trying next
                if idx < len(download_urls):
                    print(f"    ⚠ Failed, trying next URL...")
                    await asyncio.sleep(1)
            
            print(f"    ✗ All download URLs failed")
            return False
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return False
    
    async def get_all_bunkr_pages(self, base_url: str) -> list:
        """Detect and return URLs for all pages in a Bunkr album"""
        soup = await self.fetch_page(base_url)
        page_urls = [base_url]
        
        pagination_elements = soup.select('a, button')
        max_page = 1
        
        for elem in pagination_elements:
            href = elem.get('href', '')
            if '?page=' in href or '/page/' in href:
                try:
                    if '?page=' in href:
                        page_num = int(href.split('?page=')[-1].split('&')[0].split('#')[0])
                    elif '/page/' in href:
                        page_num = int(href.split('/page/')[-1].split('?')[0].split('/')[0])
                    max_page = max(max_page, page_num)
                except:
                    pass
            
            text = elem.get_text().strip()
            if text.isdigit():
                page_num = int(text)
                max_page = max(max_page, page_num)
        
        if max_page > 1:
            print(f"    → Detected {max_page} total pages")
            base_path = base_url.split('?')[0]
            for page_num in range(2, max_page + 1):
                page_url = f"{base_path}?page={page_num}"
                page_urls.append(page_url)
        
        return page_urls
    
    async def scrape_bunkr_album(self, url: str):
        """Scrape a Bunkr album with pagination support"""
        print(f"📁 Scraping Bunkr album: {url}")
        
        soup = await self.fetch_page(url)
        
        album_title = soup.select_one('h1')
        album_name = album_title.get_text().strip() if album_title else url.split('/')[-1]
        album_name = re.sub(r'[<>:"/\\|?*]', '', album_name)
        print(f"Album: {album_name}")
        
        album_dir = self.output_dir / album_name
        album_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔍 Detecting pages...")
        page_urls = await self.get_all_bunkr_pages(url)
        print(f"Found {len(page_urls)} page(s)")
        
        all_success_count = 0
        all_fail_count = 0
        all_file_count = 0
        
        for page_idx, page_url in enumerate(page_urls, 1):
            if len(page_urls) > 1:
                print(f"\n{'='*60}")
                print(f"📄 Page {page_idx}/{len(page_urls)}: {page_url}")
                print(f"{'='*60}\n")
            
            soup = await self.fetch_page(page_url)
            cards = soup.select('div.theItem')
            print(f"Found {len(cards)} files on this page\n")
            
            all_file_count += len(cards)
            
            for idx, card in enumerate(cards, 1):
                try:
                    link_elem = card.select_one('a[href^="/f/"]')
                    if not link_elem:
                        print(f"[{idx}/{len(cards)}] ⚠ No link")
                        all_fail_count += 1
                        continue
                    
                    link = link_elem.get('href')
                    parsed = urlparse(url)
                    if link.startswith('/'):
                        link = f"{parsed.scheme}://{parsed.netloc}{link}"
                    
                    print(f"[Page {page_idx}, {idx}/{len(cards)}] {link}")
                    success = await self.scrape_bunkr_file(link, album_dir)
                    
                    if success:
                        all_success_count += 1
                    else:
                        all_fail_count += 1
                        
                    print()
                    
                    if idx < len(cards):
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"[Page {page_idx}, {idx}/{len(cards)}] ✗ Error: {e}\n")
                    all_fail_count += 1
        
        print(f"\n{'='*60}")
        print(f"✓ Album complete: {album_dir}")
        print(f"📄 Total pages processed: {len(page_urls)}")
        print(f"📁 Total files found: {all_file_count}")
        print(f"✓ Successfully downloaded: {all_success_count}/{all_file_count}")
        print(f"✗ Failed: {all_fail_count}/{all_file_count}")
        print(f"{'='*60}")
    
    # ============ MAIN SCRAPER ============
    
    async def scrape(self, url: str):
        """Main scraping method - auto-detects site"""
        try:
            # Detect which site
            if 'pixeldrain.com' in url:
                # Pixeldrain doesn't need browser
                if '/l/' in url:
                    # List/album
                    list_id = url.split('/l/')[-1].split('?')[0].split('#')[0]
                    await self.scrape_pixeldrain_list(list_id)
                elif '/u/' in url or '/api/file/' in url:
                    # Single file
                    file_id = url.split('/u/')[-1].split('?')[0].split('#')[0] if '/u/' in url else url.split('/api/file/')[-1].split('?')[0]
                    await self.scrape_pixeldrain_file(file_id, self.output_dir)
                else:
                    print("❌ Invalid Pixeldrain URL")
                    
            elif 'bunkr' in url:
                # Bunkr needs browser
                await self.init_browser()
                
                if '/a/' in url:
                    await self.scrape_bunkr_album(url)
                elif '/f/' in url:
                    await self.scrape_bunkr_file(url, self.output_dir)
                else:
                    print("❌ Invalid Bunkr URL")
            else:
                print("❌ Unsupported site (only Pixeldrain and Bunkr supported)")
                
        finally:
            await self.close_browser()


class ForumImageDownloader:
    """Simpcity forum image downloader"""
    
    def __init__(self, output_dir: str = "downloads", debug_mode: bool = False):
        self.session = requests.Session()
        
        # Create cookies directory if it doesn't exist (safety net)
        self.cookies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies')
        if not os.path.exists(self.cookies_dir):
            os.makedirs(self.cookies_dir)
            # Don't print message here since main() already did it
        
        self.cookie_file = os.path.join(self.cookies_dir, 'forum_cookies.txt')
        self.download_path = output_dir
        self.debug_mode = debug_mode
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Filter settings - More lenient defaults
        self.min_file_size = 5000  # Skip files smaller than 5KB (likely broken/icons)
        self.max_dimension_to_skip = 100  # Skip images where BOTH dimensions are <= 100px
        self.skip_square_small = True  # Skip small square images
        self.max_square_size = 150  # Maximum size for square images to skip
        
        # Setup cookie jar
        self.cookie_jar = MozillaCookieJar(self.cookie_file)
        if os.path.exists(self.cookie_file):
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        self.session.cookies = self.cookie_jar
        
        # Create download folder
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
            print(f"Created download folder: {self.download_path}")
    
    def test_cookies(self):
        """Test if cookies are valid and show information"""
        print("\n" + "="*60)
        print("COOKIE DIAGNOSTICS")
        print("="*60)
        
        if not os.path.exists(self.cookie_file):
            print(f"\n✗ Cookie file '{self.cookie_file}' NOT FOUND")
            print("\nPlease create the cookie file first.")
            return False
        
        try:
            print(f"\n✓ Cookie file '{self.cookie_file}' found")
            self.cookie_jar = MozillaCookieJar(self.cookie_file)
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
            
            print(f"✓ Loaded {len(self.cookie_jar)} cookies")
            
            print("\nCookie details:")
            for cookie in self.cookie_jar:
                expires = "session" if cookie.expires is None else time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cookie.expires))
                print(f"  • {cookie.name}")
                print(f"    Domain: {cookie.domain}")
                print(f"    Expires: {expires}")
                
                if cookie.expires and cookie.expires < time.time():
                    print(f"    ⚠ WARNING: This cookie has EXPIRED!")
            
            session_cookies = ['xf_session', 'xf_user', 'PHPSESSID', 'wordpress_logged_in', 'vbulletin_session']
            found_session = False
            for cookie in self.cookie_jar:
                if any(s in cookie.name.lower() for s in session_cookies):
                    found_session = True
                    print(f"\n✓ Found session cookie: {cookie.name}")
            
            if not found_session:
                print("\n⚠ WARNING: No common session cookies found")
                print("   Make sure you exported cookies AFTER logging in")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error loading cookies: {e}")
            return False
    
    def check_image_validity(self, url):
        """Check if an image should be downloaded by examining its actual properties"""
        try:
            check_headers = self.headers.copy()
            if 'jpg6.su' in url or any(f'jpg{i}.su' in url for i in range(1, 11)):
                check_headers['Referer'] = 'https://simpcity.su/'
            
            # For CDN hosts, skip size checking - they often give incorrect sizes
            parsed = urlparse(url)
            cdn_hosts = ['jpg6.su', 'jpg1.su', 'jpg2.su', 'jpg3.su', 'jpg4.su', 'jpg5.su', 
                        'jpg7.su', 'jpg8.su', 'jpg9.su', 'jpg10.su', 'selti-delivery.ru',
                        'ibb.co', 'imgbb.com', 'i.imgur.com', 'i.redd.it']
            
            is_cdn = any(cdn in parsed.netloc for cdn in cdn_hosts)
            
            if is_cdn:
                # For CDN hosts, skip file size checking but still check dimensions
                try:
                    head_response = self.session.head(url, headers=check_headers, timeout=5, allow_redirects=True)
                    content_type = head_response.headers.get('content-type', '')
                    
                    # Only reject if we can confirm it's NOT an image
                    if content_type and 'text/html' in content_type:
                        return False, f"HTML page, not image", 0, None
                except:
                    pass  # Can't check, continue to dimension check
                
                # For CDN hosts, we'll still check dimensions below
                # but skip the file size requirement
                file_size = 0  # Don't enforce minimum file size for CDN
            else:
                # For non-CDN hosts, check file size
                try:
                    head_response = self.session.head(url, headers=check_headers, timeout=10, allow_redirects=True)
                    content_length = head_response.headers.get('content-length')
                    content_type = head_response.headers.get('content-type', '')
                    
                    if content_type and not content_type.startswith('image/'):
                        return False, f"Not an image (Content-Type: {content_type})", 0, None
                    
                    if content_length:
                        file_size = int(content_length)
                        if file_size < self.min_file_size:
                            return False, f"File too small ({file_size} bytes < {self.min_file_size})", file_size, None
                except:
                    file_size = None
            
            # Try to get dimensions
            try:
                range_headers = check_headers.copy()
                range_headers['Range'] = 'bytes=0-32768'
                
                partial_response = self.session.get(url, headers=range_headers, timeout=10, stream=True)
                
                first_chunk = b''
                for chunk in partial_response.iter_content(chunk_size=8192):
                    first_chunk += chunk
                    if len(first_chunk) >= 32768:
                        break
                
                if not file_size:
                    content_length = partial_response.headers.get('content-length')
                    if content_length:
                        file_size = int(content_length)
                    else:
                        file_size = len(first_chunk)
                
                try:
                    img = Image.open(BytesIO(first_chunk))
                    width, height = img.size
                    
                    # Only reject if BOTH dimensions are very small
                    if width <= self.max_dimension_to_skip and height <= self.max_dimension_to_skip:
                        return False, f"Dimensions too small ({width}x{height})", file_size, (width, height)
                    
                    # Check for small square images (likely avatars/icons)
                    if self.skip_square_small and width == height and width <= self.max_square_size:
                        return False, f"Small square image ({width}x{height}, likely avatar/icon)", file_size, (width, height)
                    
                    # Check for specific problematic sizes
                    problematic_sizes = [
                        (96, 96), (48, 48), (50, 62), (192, 192), 
                        (64, 64), (128, 128), (32, 32), (112, 112),
                    ]
                    
                    if (width, height) in problematic_sizes:
                        return False, f"Known thumbnail size ({width}x{height})", file_size, (width, height)
                    
                    # Image passes all checks
                    return True, "OK", file_size, (width, height)
                    
                except Exception as e:
                    # Could not determine dimensions, but if file size is reasonable, let it through
                    if file_size and file_size >= self.min_file_size:
                        return True, "Could not check dimensions, but file size OK", file_size, None
                    else:
                        # Can't verify, assume it's OK rather than reject
                        return True, "Could not verify, assuming valid", file_size, None
            except:
                # Any error in dimension checking - assume valid
                return True, "Check failed, assuming valid", 0, None
        
        except Exception as e:
            # Network error or timeout - assume valid rather than reject
            return True, f"Could not verify, assuming valid", 0, None
    
    def should_skip_image(self, url, filename, html_context=None):
        """Determine if an image should be skipped based on URL/filename patterns"""
        url_lower = url.lower()
        filename_lower = filename.lower() if filename else ""
        
        skip_gifs = True
        if skip_gifs and (url_lower.endswith('.gif') or '.gif?' in url_lower):
            return True, "GIF file"
        
        # Skip known small/system image sizes
        size_patterns = [
            r'50x62', r'96x96', r'192x192', r'300x100', r'48x48',
            r'32x32', r'64x64', r'128x128', r'150x150',
            r'_96\.', r'_48\.', r'-96\.', r'-48\.',
            r'width=["\']?96["\']?', r'height=["\']?96["\']?',
            r'width=["\']?48["\']?', r'height=["\']?48["\']?',
            r'size_96', r'size_48',
        ]
        
        for pattern in size_patterns:
            if re.search(pattern, filename_lower) or re.search(pattern, url_lower):
                return True, f"Matches size pattern: {pattern}"
        
        skip_patterns = [
            r'_thumb(?:nail)?\.', r'_small\.', r'_mini\.', r'_tiny\.', r'_icon\.',
            r'thumb_', r'small_', r'mini_', r'tiny_', r'avatar',
            r'_\d+x\d+\.', r'-\d+x\d+\.', r'_low\.', r'_lowres\.',
            r'_lowquality\.', r'_preview\.', r'_sample\.',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, filename_lower):
                return True, f"Matches skip pattern: {pattern}"
        
        skip_url_patterns = [
            '/thumbs/', '/thumbnail/', '/small/', '/mini/', '/tiny/',
            '/preview/', '/sample/', '/lowres/', '/lowquality/', '/avatar/',
            '/icon/', '/smilie/', '/emoji/', '/spacer.', '/pixel.',
            '/1x1.', '/blank.',
        ]
        
        for pattern in skip_url_patterns:
            if pattern in url_lower:
                return True, f"URL contains: {pattern}"
        
        skip_domains = ['gravatar.com', 'avatar.tapatalk-cdn.com']
        
        parsed_url = urlparse(url_lower)
        for domain in skip_domains:
            if domain in parsed_url.netloc:
                return True, f"Domain: {domain}"
        
        return False, ""
    
    def filter_images(self, img_urls, html_contents):
        """Filter out unwanted images from the URL list"""
        filtered_urls = []
        skipped_count = 0
        skip_reasons = {}
        
        combined_html = " ".join(html_contents)
        
        print("\nPhase 1: URL/Filename filtering...")
        for url in img_urls:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            
            should_skip, reason = self.should_skip_image(url, filename, combined_html)
            
            if should_skip:
                skipped_count += 1
                if reason not in skip_reasons:
                    skip_reasons[reason] = 0
                skip_reasons[reason] += 1
                continue
            
            filtered_urls.append(url)
        
        print(f"  Passed URL/filename filter: {len(filtered_urls)}/{len(img_urls)}")
        
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} by URL/filename:")
            for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {reason}: {count}")
        
        return filtered_urls
    
    def filter_by_actual_properties(self, img_urls):
        """Second phase filtering: Check actual file size and dimensions"""
        print(f"\nPhase 2: Checking actual image properties...")
        print(f"  Minimum file size: {self.min_file_size} bytes ({self.min_file_size/1024:.1f} KB)")
        print(f"  Maximum dimension for small images: {self.max_dimension_to_skip}px")
        print(f"  Skip square images up to: {self.max_square_size}x{self.max_square_size}px")
        print(f"  Note: CDN hosts (jpg6.su, etc.) are assumed valid by default")
        print(f"  Checking {len(img_urls)} images...")
        
        validated_urls = []
        skipped_by_size = 0
        skipped_by_dimensions = 0
        cdn_assumed_valid = 0
        check_failed = 0
        dimension_reasons = {}
        
        for i, url in enumerate(img_urls, 1):
            if i % 10 == 0 or i == len(img_urls):
                print(f"  Progress: {i}/{len(img_urls)}", end='\r')
            
            should_download, reason, file_size, dimensions = self.check_image_validity(url)
            
            if should_download:
                validated_urls.append(url)
                if 'CDN host' in reason or 'assumed valid' in reason:
                    cdn_assumed_valid += 1
                elif 'Could not verify' in reason or should_download is None:
                    check_failed += 1
            else:
                if 'too small' in reason.lower() and 'bytes' in reason.lower():
                    skipped_by_size += 1
                elif dimensions:
                    skipped_by_dimensions += 1
                    dim_key = f"{dimensions[0]}x{dimensions[1]}"
                    if dim_key not in dimension_reasons:
                        dimension_reasons[dim_key] = 0
                    dimension_reasons[dim_key] += 1
            
            if i < len(img_urls):
                time.sleep(0.05)  # Reduced delay since we're skipping CDN checks
        
        print()
        print(f"\n  Results:")
        print(f"    ✓ Valid images: {len(validated_urls)}")
        if cdn_assumed_valid > 0:
            print(f"    ℹ CDN hosts (assumed valid): {cdn_assumed_valid}")
        print(f"    ✗ Rejected (file size): {skipped_by_size}")
        print(f"    ✗ Rejected (dimensions): {skipped_by_dimensions}")
        if dimension_reasons:
            print(f"    Common dimensions skipped:")
            for dim, count in sorted(dimension_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      - {dim}: {count} images")
        if check_failed > 0:
            print(f"    ℹ Could not verify (included): {check_failed}")
        
        return validated_urls
    
    def detect_pagination(self, html_content, base_url):
        """Detect pagination links in forum threads"""
        page_urls = set()
        
        action_keywords = [
            '/report', '/share', '/bookmark', '/react', '/reactions',
            '/edit', '/delete', '/reply', '/quote', '/like', '/unlike',
            '/watch', '/unwatch', '/ignore', '/warn', '/ban',
            '/vote', '/poll', '/rating', '/subscribe', '/unsubscribe',
            '/mark-read', '/mark-unread', '/print', '/email',
            '/alert', '/conversation', '/find-new', '/find-threads',
            '/watched', '/search', '/login', '/register', '/logout'
        ]
        
        pagination_patterns = [
            r'href=["\']([^"\']+?(?:page|p|pg|pagina|pag)=\d+[^"\']*)["\']',
            r'href=["\']([^"\']+?/(?:page/|p/)?\d+/[^"\']*)["\']',
            r'href=["\']([^"\']+?showtopic=\d+&(?:st|page)=\d+[^"\']*)["\']',
        ]
        
        for pattern in pagination_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match:
                    if any(action in match.lower() for action in action_keywords):
                        continue
                    
                    if not match.startswith(('http://', 'https://')):
                        match = urljoin(base_url, match)
                    page_urls.add(match)
        
        numbered_pattern = r'<a[^>]+href=["\']([^"\']+?)["\'][^>]*>\s*\d+\s*</a>'
        numbered_matches = re.findall(numbered_pattern, html_content, re.IGNORECASE)
        for match in numbered_matches:
            if match and '#' not in match:
                if any(action in match.lower() for action in action_keywords):
                    continue
                
                if not match.startswith(('http://', 'https://')):
                    match = urljoin(base_url, match)
                page_urls.add(match)
        
        nav_patterns = [
            r'<a[^>]+href=["\']([^"\']+?)["\'][^>]*>(?:next|>|»|&gt;|&raquo;)</a>',
            r'<a[^>]+href=["\']([^"\']+?)["\'][^>]*>(?:prev|previous|<|«|&lt;|&laqua;)</a>',
            r'class=["\'](?:next|prev|pagination)[^>]+href=["\']([^"\']+?)["\']',
        ]
        
        for pattern in nav_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match:
                    if any(action in match.lower() for action in action_keywords):
                        continue
                    
                    if not match.startswith(('http://', 'https://')):
                        match = urljoin(base_url, match)
                    page_urls.add(match)
        
        page_urls.add(base_url)
        
        cleaned_urls = set()
        for url in page_urls:
            url_lower = url.lower()
            if not any(action in url_lower for action in action_keywords):
                cleaned_urls.add(url)
        
        return cleaned_urls
    
    def extract_page_numbers(self, page_urls):
        """Extract page numbers from URLs to sort them"""
        page_data = []
        
        for url in page_urls:
            page_num = 1
            
            page_param_match = re.search(r'[?&](?:page|p|pg|pagina|pag)=(\d+)', url, re.IGNORECASE)
            if page_param_match:
                page_num = int(page_param_match.group(1))
            else:
                path_match = re.search(r'/(?:page/|p/)?(\d+)/', url)
                if path_match:
                    page_num = int(path_match.group(1))
                else:
                    end_match = re.search(r'/(\d+)$', url)
                    if end_match:
                        page_num = int(end_match.group(1))
            
            page_data.append((page_num, url))
        
        page_data.sort(key=lambda x: x[0])
        
        seen = set()
        unique_pages = []
        for page_num, url in page_data:
            if url not in seen:
                seen.add(url)
                unique_pages.append((page_num, url))
        
        return unique_pages
    
    def scrape_all_pages(self, start_url):
        """Scrape all pages of a forum thread"""
        print(f"\nDetecting pagination for: {start_url}")
        print("-" * 60)
        
        try:
            response = self.session.get(start_url, headers=self.headers, timeout=30)
            
            if self.debug_mode:
                print(f"\nDEBUG: Response status code: {response.status_code}")
                print(f"DEBUG: Response URL: {response.url}")
            
            login_indicators = ['please login', 'sign in required', 'you must be logged in', 'login to view', 'restricted access']
            response_lower = response.text.lower()
            
            if response.status_code in [401, 403]:
                print("✗ Access denied (HTTP 401/403)")
                login_required = True
            else:
                found_indicators = [ind for ind in login_indicators if ind in response_lower]
                
                if found_indicators:
                    content_indicators = ['<div class="message', '<article', 'post-', 'thread-', 'bbcode', '[img]']
                    has_content = any(ind in response_lower for ind in content_indicators)
                    
                    login_required = not (has_content and len(response.text) > 5000)
                else:
                    login_required = False
            
            if login_required:
                print("✗ Login required or session expired!")
                print(f"\nPlease ensure '{self.cookie_file}' exists with valid cookies")
                print("Export cookies from your browser after logging in to the forum")
                return [], []
            
            response.raise_for_status()
            print("✓ Successfully accessed first page")
            
            page_urls = self.detect_pagination(response.text, start_url)
            sorted_pages = self.extract_page_numbers(page_urls)
            
            if len(sorted_pages) <= 1:
                print("✓ Single page thread detected")
                return [start_url], [response.text]
            
            print(f"✓ Found {len(sorted_pages)} pages")
            
            print(f"\n{'='*60}")
            print("MULTI-PAGE THREAD DETECTED")
            print('='*60)
            print(f"\nThis thread has {len(sorted_pages)} pages.")
            print("\nDownload options:")
            print("1. Download from ALL pages")
            print("2. Download from current page only")
            print("3. Specify page range (e.g., 1-5 or 3,4,5)")
            
            choice = input("\nChoose option (1/2/3): ").strip()
            
            pages_to_scrape = []
            
            if choice == '1':
                pages_to_scrape = [url for _, url in sorted_pages]
                print(f"✓ Will download from all {len(pages_to_scrape)} pages")
            elif choice == '2':
                pages_to_scrape = [start_url]
                print("✓ Will download from current page only")
            elif choice == '3':
                page_range = input("Enter page range (e.g., 1-5) or specific pages (e.g., 1,3,5): ").strip()
                
                if '-' in page_range:
                    try:
                        start, end = map(int, page_range.split('-'))
                        for page_num, url in sorted_pages:
                            if start <= page_num <= end:
                                pages_to_scrape.append(url)
                        print(f"✓ Will download from pages {start} to {end}")
                    except:
                        print("✗ Invalid range format. Using all pages.")
                        pages_to_scrape = [url for _, url in sorted_pages]
                elif ',' in page_range:
                    try:
                        page_numbers = [int(p.strip()) for p in page_range.split(',')]
                        for page_num, url in sorted_pages:
                            if page_num in page_numbers:
                                pages_to_scrape.append(url)
                        print(f"✓ Will download from pages: {page_range}")
                    except:
                        print("✗ Invalid page list. Using all pages.")
                        pages_to_scrape = [url for _, url in sorted_pages]
                else:
                    try:
                        page_num = int(page_range)
                        for p_num, url in sorted_pages:
                            if p_num == page_num:
                                pages_to_scrape.append(url)
                                break
                        print(f"✓ Will download from page {page_num}")
                    except:
                        print("✗ Invalid page number. Using all pages.")
                        pages_to_scrape = [url for _, url in sorted_pages]
            else:
                pages_to_scrape = [url for _, url in sorted_pages]
                print(f"✓ Will download from all {len(pages_to_scrape)} pages")
            
            all_html_contents = []
            print(f"\nScraping {len(pages_to_scrape)} pages...")
            
            rate_limit_delay = 0.5
            consecutive_failures = 0
            
            for i, page_url in enumerate(pages_to_scrape, 1):
                try:
                    print(f"  [{i}/{len(pages_to_scrape)}] Fetching page {i}...")
                    
                    page_response = self.session.get(page_url, headers=self.headers, timeout=30)
                    page_response.raise_for_status()
                    all_html_contents.append(page_response.text)
                    
                    consecutive_failures = 0
                    
                    if i < len(pages_to_scrape):
                        time.sleep(rate_limit_delay)
                        
                except requests.exceptions.HTTPError as e:
                    if '429' in str(e):
                        consecutive_failures += 1
                        rate_limit_delay = min(5.0, rate_limit_delay * 2)
                        print(f"  ✗ Rate limited (429). Slowing down... (delay now {rate_limit_delay}s)")
                        time.sleep(rate_limit_delay)
                    else:
                        print(f"  ✗ Failed to fetch page {i}: {e}")
                    
                    consecutive_failures += 1
                    
                    if consecutive_failures >= 10:
                        print(f"\n  ⚠ Too many consecutive failures. Stopping pagination.")
                        break
                        
                except Exception as e:
                    print(f"  ✗ Failed to fetch page {i}: {e}")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= 10:
                        print(f"\n  ⚠ Too many consecutive failures. Stopping pagination.")
                        break
            
            if not all_html_contents:
                print("✗ No pages were successfully fetched.")
                return [], []
            
            if consecutive_failures > 0:
                print(f"\n⚠ Warning: {consecutive_failures} pages failed to fetch")
            
            print(f"✓ Successfully scraped {len(all_html_contents)} pages")
            
            return pages_to_scrape, all_html_contents
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error accessing page: {e}")
            return [], []
    
    def extract_images_improved(self, html_content, base_url):
        """Improved extraction for all image URLs from HTML content"""
        img_urls = set()
        
        # PRIORITY 1: data-url attributes (has the full URLs for lazy-loaded images)
        data_url_pattern = r'<img[^>]*?data-url=["\']([^"\']+?)["\'][^>]*?>'
        data_url_matches = re.findall(data_url_pattern, html_content, re.IGNORECASE)
        for match in data_url_matches:
            if match and len(match) > 15 and not match.startswith('data:'):
                img_urls.add(match)
        
        # PRIORITY 2: Other data attributes
        data_attrs_patterns = [
            r'<img[^>]*?data-src=["\']([^"\']+?)["\'][^>]*?>',
            r'<img[^>]*?data-original=["\']([^"\']+?)["\'][^>]*?>',
            r'<img[^>]*?data-zoom-image=["\']([^"\']+?)["\'][^>]*?>',
            r'<img[^>]*?data-full=["\']([^"\']+?)["\'][^>]*?>',
            r'<img[^>]*?data-large=["\']([^"\']+?)["\'][^>]*?>',
        ]
        
        for pattern in data_attrs_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 15 and not match.startswith('data:'):
                    img_urls.add(match)
        
        # NOTE: jpg6.su links are just for clicking - the forum HTML already has
        # the direct image URLs in src/data-url attributes, so we don't need to scrape them!
        
        # PRIORITY 3: Plain URLs in text
        url_patterns = [
            r'(https?://(?:simp\d+|cdn)\.selti-delivery\.ru/[^\s<>"\']+?\.(?:jpg|jpeg|png|gif|webp))',
            r'(https?://(?:ibb\.co|i\.ibb\.co|imgbb\.com)/[^\s<>"\']+)',
            r'(https?://(?:i\.imgur\.com|imgur\.com)/[^\s<>"\']+?\.(?:jpg|jpeg|png|gif|webp))',
            r'(https?://i\.redd\.it/[^\s<>"\']+?\.(?:jpg|jpeg|png|gif|webp))',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 15:
                    img_urls.add(match)
        
        # PRIORITY 4: Links to images (often full-size versions)
        link_patterns = [
            r'<a[^>]*?href=["\']([^"\']+?\.(?:jpg|jpeg|png|gif|bmp|webp)(?:\?[^"\']*)?)["\'][^>]*?>',
            r'<a[^>]*?class=["\'][^"\']*?(?:lightbox|zoom|fancybox|gallery)[^"\']*?["\'][^>]*?href=["\']([^"\']+?)["\'][^>]*?>',
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 15:
                    img_urls.add(match)
        
        # PRIORITY 5: Regular img src tags
        # Extract these even if they don't have explicit extensions in the URL,
        # as long as they're not data: URIs
        img_src_pattern = r'<img[^>]*?src=["\']([^"\']+?)["\'][^>]*?>'
        img_src_matches = re.findall(img_src_pattern, html_content, re.IGNORECASE)
        for match in img_src_matches:
            if match and len(match) > 15 and not match.startswith('data:'):
                # Only add if it looks like a real image URL
                if any(ext in match.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.md.']):
                    img_urls.add(match)
        
        # Clean and normalize URLs
        clean_urls = set()
        for url in img_urls:
            if url and not url.startswith('data:'):
                url = url.strip()
                url = url.replace('&amp;', '&')
                url = url.replace('&quot;', '')
                if ' ' in url:
                    url = url.split(' ')[0]
                url = url.replace('\\/', '/').replace('\\', '')
                
                # Handle protocol-relative URLs
                if url.startswith('//'):
                    url = 'https:' + url
                elif not url.startswith(('http://', 'https://')):
                    if url.startswith('/'):
                        url = urljoin(base_url, url)
                    else:
                        continue
                
                # Special handling for ibb.co
                parsed = urlparse(url)
                if 'ibb.co' in parsed.netloc:
                    if not parsed.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        url = url.rstrip('/') + '.jpg'
                
                # Remove URL fragments
                url = url.split('#')[0]
                
                clean_urls.add(url)
        
        return clean_urls
    
    def get_high_resolution_images(self, img_urls):
        """Try to get higher resolution versions of images"""
        high_res_urls = set()
        
        for url in img_urls:
            high_res = url
            
            replacements = [
                ('/thumb/', '/'), ('/thumbnail/', '/'), ('/thumbs/', '/'),
                ('/small/', '/'), ('/medium/', '/'), ('/large/', '/'),
                ('_thumb', ''), ('_small', ''), ('_medium', ''),
                ('thumb_', ''), ('small_', ''),
                ('-150x150.', '.'), ('-300x300.', '.'),
                ('_150x150.', '.'), ('_300x300.', '.'),
            ]
            
            for old, new in replacements:
                if old in high_res.lower():
                    high_res = high_res.replace(old, new)
            
            high_res_urls.add(high_res)
            
            if 'jpg6.su' in high_res.lower():
                size_pattern = r'[_-]\d+x\d+'
                no_size = re.sub(size_pattern, '', high_res)
                high_res_urls.add(no_size)
        
        return high_res_urls
    
    def get_prefixed_filename(self, url, index, prefix):
        """Generate filename with user prefix"""
        prefix = re.sub(r'[<>:"/\\|?*]', '_', prefix)
        
        parsed = urlparse(url)
        original_filename = os.path.basename(parsed.path)
        
        if '.' in original_filename:
            ext_match = re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg)', original_filename, re.IGNORECASE)
            if ext_match:
                ext = '.' + ext_match.group(1).lower()
                if ext.lower() == '.jpeg':
                    ext = '.jpg'
            else:
                ext = '.jpg'
        else:
            ext = '.jpg'
        
        filename = f"{prefix}{index:04d}{ext}"
        
        return filename
    
    def download_images(self, forum_url):
        """Main download function with improved filtering"""
        print(f"\nProcessing: {forum_url}")
        print("-" * 60)
        
        page_urls, html_contents = self.scrape_all_pages(forum_url)
        
        if not html_contents:
            print("✗ No content to process.")
            return
        
        all_img_urls = set()
        total_pages = len(html_contents)
        
        # Save HTML for debugging if in debug mode
        if self.debug_mode and html_contents:
            debug_dir = os.path.join(self.download_path, "debug_html")
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            for i, html_content in enumerate(html_contents, 1):
                debug_file = os.path.join(debug_dir, f"page_{i}.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            print(f"\nDEBUG: Saved HTML to {debug_dir}/")
        
        print(f"\nExtracting images from {total_pages} pages...")
        
        for i, html_content in enumerate(html_contents, 1):
            print(f"  Processing page {i}/{total_pages}...")
            page_img_urls = self.extract_images_improved(html_content, forum_url)
            
            jpg6_count = len([u for u in page_img_urls if 'jpg6.su' in u])
            selti_count = len([u for u in page_img_urls if 'selti-delivery.ru' in u])
            
            print(f"    Found {len(page_img_urls)} unique URLs (jpg6.su: {jpg6_count}, selti: {selti_count})")
            
            all_img_urls.update(page_img_urls)
        
        # Try to find higher resolution versions
        if all_img_urls:
            print("  Checking for higher resolution versions...")
            high_res_urls = self.get_high_resolution_images(all_img_urls)
            all_img_urls = all_img_urls.union(high_res_urls)
        
        print(f"\nTotal unique image URLs found: {len(all_img_urls)}")
        
        # Show sample URLs for debugging
        if all_img_urls:
            sample_urls = list(all_img_urls)[:5]
            print("\nSample URLs extracted:")
            for i, url in enumerate(sample_urls, 1):
                print(f"  {i}. {url[:100]}{'...' if len(url) > 100 else ''}")
        
        print("\nImage hosting breakdown:")
        host_counts = {}
        for url in all_img_urls:
            parsed = urlparse(url)
            host = parsed.netloc
            host_counts[host] = host_counts.get(host, 0) + 1
        
        for host, count in sorted(host_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {host}: {count} images")
        
        all_img_urls_list = list(all_img_urls)
        
        print(f"\n{'='*60}")
        print("FILTERING PHASE 1: URL/Filename patterns")
        print('='*60)
        filtered_img_urls = self.filter_images(all_img_urls_list, html_contents)
        
        if not filtered_img_urls:
            print("✗ No images remained after URL/filename filtering.")
            return
        
        print(f"\n{'='*60}")
        print("FILTERING PHASE 2: Actual image properties")
        print('='*60)
        
        print(f"\nPhase 1 passed: {len(filtered_img_urls)} images")
        print("\nWould you like to check actual image dimensions and file sizes?")
        print("⚠ WARNING: This can be overly aggressive and filter out valid images,")
        print("  especially on CDN hosts like jpg6.su. Consider skipping for forum downloads.")
        print("\n1. Yes, check all images (may filter too many)")
        print("2. No, skip property checking (recommended for forums)")
        
        check_choice = input("\nChoose option (1/2): ").strip()
        if not check_choice:
            check_choice = '2'  # Default to skip
        
        if check_choice == '1':
            validated_img_urls = self.filter_by_actual_properties(filtered_img_urls)
            
            # Check if too many were filtered
            filtered_percentage = ((len(filtered_img_urls) - len(validated_img_urls)) / len(filtered_img_urls) * 100) if filtered_img_urls else 0
            
            if filtered_percentage > 80:
                print(f"\n{'='*60}")
                print("⚠ WARNING: Property checking filtered out {:.0f}% of images!".format(filtered_percentage))
                print('='*60)
                print(f"This suggests the filters may be too aggressive for this forum.")
                print(f"Only {len(validated_img_urls)} out of {len(filtered_img_urls)} images passed.")
                print("\nOptions:")
                print("1. Continue with these {0} images".format(len(validated_img_urls)))
                print("2. Skip property checking and use all {0} images from Phase 1".format(len(filtered_img_urls)))
                
                choice = input("\nChoose option (1/2): ").strip()
                if choice == '2':
                    validated_img_urls = filtered_img_urls
                    print(f"✓ Using all {len(filtered_img_urls)} images from Phase 1")
        else:
            validated_img_urls = filtered_img_urls
            print("✓ Skipped property checking")
        
        if not validated_img_urls:
            print("✗ No images remained after filtering.")
            return
        
        print(f"\n✓ Final count: {len(validated_img_urls)} images after all filtering")
        
        if validated_img_urls:
            print("\nSample of found images:")
            for i, img_url in enumerate(validated_img_urls[:5], 1):
                filename = os.path.basename(urlparse(img_url).path)
                print(f"  {i}. {filename[:50]}... ({urlparse(img_url).netloc})")
            if len(validated_img_urls) > 5:
                print(f"  ... and {len(validated_img_urls) - 5} more")
        
        print("\n" + "="*60)
        print("FILENAME SETTINGS")
        print("="*60)
        
        suggested_prefix = ""
        parsed_url = urlparse(forum_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if path_parts:
            for part in reversed(path_parts):
                if part and not part.isdigit() and len(part) > 2:
                    clean_part = re.sub(r'[^a-zA-Z0-9_-]', '_', part)
                    suggested_prefix = clean_part + '_'
                    break
        
        if not suggested_prefix:
            suggested_prefix = "image_"
        
        print(f"\nSuggested prefix: '{suggested_prefix}'")
        prefix = input(f"Enter filename prefix (press Enter for '{suggested_prefix}'): ").strip()
        
        if not prefix:
            prefix = suggested_prefix
        
        print("\nOverwrite existing files?")
        overwrite = input("(y)es, (n)o (skip), (a)uto-rename: ").strip().lower()
        if overwrite not in ['y', 'n', 'a']:
            overwrite = 'a'
        
        print("\nFile type filtering:")
        print("1. Download only JPG/JPEG/PNG files")
        print("2. Download all image types")
        print("3. Skip GIF files only")
        
        filetype_choice = input("Choose option (1/2/3): ").strip()
        
        print(f"\n{'-'*60}")
        proceed = input(f"Download {len(validated_img_urls)} images from {total_pages} pages? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("Download cancelled.")
            return
        
        successful = 0
        skipped = 0
        failed = 0
        filtered_by_type = 0
        failed_urls = []  # Track failed URLs
        
        print(f"\n{'='*60}")
        print("DOWNLOADING IMAGES")
        print('='*60)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        thread_name = "thread"
        parsed_url = urlparse(forum_url)
        path_parts = parsed_url.path.strip('/').split('/')
        if path_parts:
            for part in reversed(path_parts):
                if part and not part.isdigit() and len(part) > 2:
                    thread_name = part
                    break
        
        download_subfolder = os.path.join(self.download_path, f"{thread_name}_{timestamp}")
        if not os.path.exists(download_subfolder):
            os.makedirs(download_subfolder)
        
        for i, img_url in enumerate(validated_img_urls, 1):
            parsed = urlparse(img_url)
            filename = os.path.basename(parsed.path)
            file_ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''
            
            if filetype_choice == '1':
                if file_ext not in ['.jpg', '.jpeg', '.png']:
                    filtered_by_type += 1
                    continue
            elif filetype_choice == '3':
                if file_ext in ['.gif']:
                    filtered_by_type += 1
                    continue
            
            if prefix:
                final_filename = self.get_prefixed_filename(img_url, i, prefix)
            else:
                final_filename = filename
            
            save_path = os.path.join(download_subfolder, final_filename)
            
            if os.path.exists(save_path):
                if overwrite == 'n':
                    print(f"[{i}/{len(validated_img_urls)}] Skipped (exists): {final_filename[:40]}...")
                    skipped += 1
                    continue
                elif overwrite == 'a':
                    base_name, ext = os.path.splitext(final_filename)
                    counter = 1
                    while os.path.exists(save_path):
                        final_filename = f"{base_name}_{counter}{ext}"
                        save_path = os.path.join(download_subfolder, final_filename)
                        counter += 1
            
            try:
                print(f"[{i}/{len(validated_img_urls)}] Downloading: {final_filename[:40]}...")
                
                download_headers = self.headers.copy()
                if 'jpg6.su' in img_url or any(f'jpg{i}.su' in img_url for i in range(1, 11)):
                    download_headers['Referer'] = 'https://simpcity.su/'
                    download_headers['Accept'] = 'image/webp,image/apng,image/*,*/*;q=0.8'
                
                for attempt in range(3):
                    try:
                        img_response = self.session.get(img_url, headers=download_headers, 
                                                      stream=True, timeout=60)
                        img_response.raise_for_status()
                        break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                        if attempt < 2:
                            print(f"  Retry ({attempt+1}/3)...")
                            time.sleep(2)
                            continue
                        else:
                            raise
                
                content_type = img_response.headers.get('content-type', '')
                if content_type and not content_type.startswith('image/'):
                    print(f"  ⚠ Not an image (Content-Type: {content_type})")
                
                file_size = int(img_response.headers.get('content-length', 0))
                
                with open(save_path, 'wb') as f:
                    if file_size == 0:
                        f.write(img_response.content)
                    else:
                        for chunk in img_response.iter_content(chunk_size=32768):
                            if chunk:
                                f.write(chunk)
                
                actual_size = os.path.getsize(save_path)
                
                if actual_size < 2048:
                    print(f"  ⚠ File very small ({actual_size} bytes), may not be valid image")
                    os.remove(save_path)
                    failed += 1
                else:
                    size_kb = actual_size / 1024
                    if size_kb > 1024:
                        size_mb = size_kb / 1024
                        print(f"  ✓ Saved ({size_mb:.2f} MB)")
                    else:
                        print(f"  ✓ Saved ({size_kb:.1f} KB)")
                    successful += 1
                
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg:
                    print(f"  ✗ Failed: 404 Not Found")
                    failed_urls.append((img_url, "404 Not Found"))
                elif "403" in error_msg:
                    print(f"  ✗ Failed: 403 Forbidden")
                    failed_urls.append((img_url, "403 Forbidden"))
                elif "timeout" in error_msg.lower():
                    print(f"  ✗ Failed: Timeout")
                    failed_urls.append((img_url, "Timeout"))
                else:
                    print(f"  ✗ Failed: {type(e).__name__}")
                    failed_urls.append((img_url, f"{type(e).__name__}: {error_msg[:50]}"))
                failed += 1
            
            if i < len(validated_img_urls):
                if 'jpg6.su' in img_url or any(f'jpg{i}.su' in img_url for i in range(1, 11)):
                    time.sleep(1.0)
                else:
                    time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print("DOWNLOAD SUMMARY")
        print('='*60)
        print(f"Pages processed: {total_pages}")
        print(f"Total URLs found: {len(all_img_urls_list)}")
        print(f"Filtered by URL/filename: {len(all_img_urls_list) - len(filtered_img_urls)}")
        if check_choice == '1':
            print(f"Filtered by size/dimensions: {len(filtered_img_urls) - len(validated_img_urls)}")
        print(f"Filtered by file type: {filtered_by_type}")
        print(f"Successfully downloaded: {successful}")
        print(f"Skipped (already existed): {skipped}")
        print(f"Failed: {failed}")
        print(f"Location: {download_subfolder}")
        
        if successful > 0:
            print(f"\n✓ Download successful!")
            try:
                if sys.platform == 'win32':
                    os.startfile(download_subfolder)
            except:
                pass
        else:
            print(f"\n✗ No images were downloaded successfully.")
        
        # Save failed URLs for debugging
        if failed > 0 and failed_urls:
            failed_file = os.path.join(download_subfolder, "failed_urls.txt")
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write(f"Failed URLs from {forum_url}\n")
                f.write(f"Downloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total failed: {failed}/{len(validated_img_urls)}\n")
                f.write("="*80 + "\n\n")
                for url, error in failed_urls[:100]:  # Save first 100
                    f.write(f"ERROR: {error}\n")
                    f.write(f"URL: {url}\n")
                    f.write("-"*80 + "\n")
            print(f"\nSaved failed URLs to: {failed_file}")
            print(f"(First {min(100, len(failed_urls))} of {len(failed_urls)} failures)")


class GenericGalleryDownloader:
    """Generic image AND video downloader for gallery sites like viralthots.tv"""
    
    def __init__(self, output_dir: str = "downloads"):
        self.session = requests.Session()
        self.download_path = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Create download folder
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
            print(f"Created download folder: {self.download_path}")
    
    def extract_from_embed_pages(self, html_content, base_url):
        """Extract iframe embed URLs and fetch video sources from them"""
        video_urls = set()
        
        # Pattern 1: Find iframe src URLs
        iframe_patterns = [
            r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>',
            r'<iframe[^>]+src=["\']([^"\']+/embed/[^"\']+)["\'][^>]*>',
        ]
        
        embed_urls = set()
        for pattern in iframe_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and not match.startswith('data:'):
                    # Normalize URL
                    if match.startswith('//'):
                        match = 'https:' + match
                    elif match.startswith('/'):
                        match = urljoin(base_url, match)
                    embed_urls.add(match)
        
        if not embed_urls:
            return video_urls
        
        print(f"  Found {len(embed_urls)} iframe embed(s), fetching video sources...")
        
        # Fetch each embed page and extract video sources
        for embed_url in embed_urls:
            try:
                print(f"    → Fetching embed: {embed_url[:60]}...")
                response = self.session.get(embed_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                embed_html = response.text
                
                # Extract video sources from embed page
                video_patterns = [
                    # HTML5 video source tags
                    r'<video[^>]+src=["\']([^"\']+)["\']',
                    r'<source[^>]+src=["\']([^"\']+\.(?:mp4|webm|mov|avi|mkv))["\']',
                    # Direct video URLs in JavaScript
                    r'["\'](https?://[^"\']+\.(?:mp4|webm|mov|avi|mkv))["\']',
                    # Common video player variable patterns
                    r'video_url\s*[:=]\s*["\']([^"\']+)["\']',
                    r'source\s*[:=]\s*["\']([^"\']+\.(?:mp4|webm|mov))["\']',
                    r'file\s*[:=]\s*["\']([^"\']+\.(?:mp4|webm|mov))["\']',
                    # JSON-style patterns
                    r'"url"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
                    r'"source"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
                    r'"file"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, embed_html, re.IGNORECASE)
                    for match in matches:
                        if match and len(match) > 15 and not match.startswith('data:'):
                            # Normalize URL
                            if match.startswith('//'):
                                match = 'https:' + match
                            elif match.startswith('/'):
                                match = urljoin(embed_url, match)
                            
                            # Skip player scripts and non-video URLs
                            if not any(skip in match.lower() for skip in ['player.js', 'analytics', 'ads', '.js', '.css']):
                                video_urls.add(match)
                                print(f"      ✓ Found video: {match[:60]}...")
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"      ✗ Failed to fetch embed: {e}")
                continue
        
        return video_urls
    
    def extract_images_from_gallery(self, html_content, base_url):
        """Specialized extraction for gallery sites - includes images AND videos"""
        img_urls = set()
        
        # Pattern 1: Direct image/video links in href attributes
        gallery_patterns = [
            r'href=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
            r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
            r'data-src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
            r'data-original=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
            r'data-full=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
        ]
        
        for pattern in gallery_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            img_urls.update(matches)
        
        # Pattern 2: Video tags (HTML5 video)
        video_patterns = [
            r'<video[^>]+src=["\'](https?://[^"\']+)["\']',
            r'<source[^>]+src=["\'](https?://[^"\']+\.(?:mp4|webm|mov|avi|mkv))["\']',
        ]
        
        for pattern in video_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            img_urls.update(matches)
        
        # Pattern 3: Look for gallery-specific patterns (like /uploads/gallery/)
        upload_pattern = r'(https?://[^"\']+/uploads/[^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))'
        upload_matches = re.findall(upload_pattern, html_content, re.IGNORECASE)
        img_urls.update(upload_matches)
        
        # Pattern 4: Look for JSON data that might contain image/video URLs
        json_patterns = [
            r'"url"\s*:\s*["\']([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
            r'"image"\s*:\s*["\']([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp))["\']',
            r'"video"\s*:\s*["\']([^"\']+\.(?:mp4|webm|mov|avi|mkv))["\']',
            r'"src"\s*:\s*["\']([^"\']+\.(?:jpg|jpeg|png|gif|bmp|webp|mp4|webm|mov|avi|mkv))["\']',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            img_urls.update(matches)
        
        # Filter and clean URLs
        clean_urls = set()
        for url in img_urls:
            if url and not url.startswith('data:'):
                url = url.replace('\\/', '/').replace('\\', '')
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = urljoin(base_url, url)
                clean_urls.add(url)
        
        return clean_urls
    
    def extract_images_generic(self, html_content, base_url):
        """Generic extraction for all types of sites - includes images AND videos"""
        img_urls = set()
        
        patterns = [
            r'<img[^>]+src=["\']([^"\'>]+)["\']',
            r'<video[^>]+src=["\']([^"\'>]+)["\']',
            r'<source[^>]+src=["\']([^"\'>]+)["\']',
            r'<source[^>]+srcset=["\']([^"\'>]+)["\']',
            r'<a[^>]+href=["\']([^"\'>]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg|ico|mp4|webm|mov|avi|mkv))["\']',
            r'background(?:-image)?\s*:\s*url\(["\']?([^"\'\)]+)["\']?\)',
            r'data-(?:src|original|large|full|image|source|video)=["\']([^"\'>]+)["\']',
            r'property=["\'](?:og:image|og:video|twitter:image|twitter:player)["\'][^>]+content=["\']([^"\'>]+)["\']',
            r'content=["\']([^"\'>]+\.(?:jpg|jpeg|png|gif|webp|mp4|webm))["\'][^>]+property=["\'](?:og:image|og:video|twitter:image)["\']',
            r'(https?://[^"\'\s<>]+\.(?:jpg|jpeg|png|gif|bmp|webp|svg|ico|mp4|webm|mov|avi|mkv)(?:\?[^"\'\s<>]*)?)',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                img_urls.update(matches)
            except:
                continue
        
        # Clean and normalize URLs
        clean_urls = set()
        for url in img_urls:
            if url and not url.startswith('data:'):
                url = url.strip()
                if ' ' in url:
                    url = url.split(' ')[0]
                if url.startswith('//'):
                    url = 'https:' + url
                elif not url.startswith(('http://', 'https://')):
                    url = urljoin(base_url, url)
                clean_urls.add(url)
        
        return clean_urls
    
    def get_high_resolution_images(self, img_urls):
        """Try to get higher resolution versions of images"""
        high_res_urls = set()
        
        for url in img_urls:
            high_res = url
            
            replacements = [
                ('/thumb/', '/full/'), ('/thumbnail/', '/original/'),
                ('/small/', '/large/'), ('/medium/', '/large/'),
                ('_thumb', ''), ('_small', ''), ('_medium', '_large'),
                ('thumb_', ''), ('/thumbs/', '/images/'),
                ('-150x150.', '.'), ('-300x300.', '.'), ('-600x600.', '.'),
                ('_150x150.', '.'), ('_300x300.', '.'), ('_600x600.', '.'),
            ]
            
            for old, new in replacements:
                if old in high_res.lower():
                    high_res = high_res.replace(old, new)
            
            high_res_urls.add(high_res)
        
        return high_res_urls
    
    def is_video_url(self, url):
        """Detect if URL is a video based on extension or URL patterns"""
        # Check 1: URL contains video extension
        if any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov', '.avi', '.mkv']):
            return True
        
        # Check 2: URL patterns that indicate video (even without extension)
        video_patterns = [
            'get_file',      # viralthots.tv video URLs
            'v-acctoken',    # Token-based video URLs
            '/video/',       # Video path
            '/stream/',      # Streaming video
            'player',        # Video player URLs
        ]
        return any(pattern in url.lower() for pattern in video_patterns)
    
    def get_prefixed_filename(self, url, index, prefix, is_video=False):
        """Generate filename with user prefix - supports images and videos"""
        prefix = re.sub(r'[<>:"/\\|?*]', '_', prefix)
        
        parsed = urlparse(url)
        original_filename = os.path.basename(parsed.path)
        
        # Remove query parameters from filename
        if '?' in original_filename:
            original_filename = original_filename.split('?')[0]
        
        if '.' in original_filename:
            # Try to extract extension for both images and videos
            ext_match = re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|svg|mp4|webm|mov|avi|mkv)', original_filename, re.IGNORECASE)
            if ext_match:
                ext = '.' + ext_match.group(1).lower()
                if ext.lower() == '.jpeg':
                    ext = '.jpg'
            else:
                # No recognized extension, use default based on type
                ext = '.mp4' if is_video else '.jpg'
        else:
            # No extension at all, use default based on type
            ext = '.mp4' if is_video else '.jpg'
        
        filename = f"{prefix}{index:03d}{ext}"
        return filename
    
    def download_images(self, url):
        """Main download function - downloads images AND videos"""
        print(f"\n📷 Processing gallery/video page: {url}")
        print("-" * 60)
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Check if it's a gallery or video site
            is_gallery = any(keyword in url.lower() for keyword in 
                           ['viralthots.tv', 'album', 'gallery', 'photos', 'video'])
            
            if is_gallery:
                print("✓ Detected gallery/video site, using specialized extraction...")
                img_urls = self.extract_images_from_gallery(response.text, url)
                
                # Also check for iframe embeds
                embed_videos = self.extract_from_embed_pages(response.text, url)
                if embed_videos:
                    print(f"  ✓ Extracted {len(embed_videos)} video(s) from iframe embeds")
                    img_urls = img_urls.union(embed_videos)
            else:
                print("✓ Using generic media extraction...")
                img_urls = self.extract_images_generic(response.text, url)
                
                # Also check for iframe embeds
                embed_videos = self.extract_from_embed_pages(response.text, url)
                if embed_videos:
                    print(f"  ✓ Extracted {len(embed_videos)} video(s) from iframe embeds")
                    img_urls = img_urls.union(embed_videos)
            
            # Try to get higher resolution versions
            if img_urls:
                print("  Checking for higher resolution versions...")
                high_res_urls = self.get_high_resolution_images(img_urls)
                img_urls = img_urls.union(high_res_urls)
            
            # Remove tiny images (likely icons, avatars, etc.) but keep videos
            filtered_urls = set()
            skip_keywords = ['avatar', 'icon', 'logo', 'spacer', 'pixel', 
                           'placeholder', 'emoji', 'smiley', 'widget']
            for img_url in img_urls:
                # Don't skip videos based on keywords
                is_video = self.is_video_url(img_url)
                if is_video or not any(keyword in img_url.lower() for keyword in skip_keywords):
                    filtered_urls.add(img_url)
            
            img_urls = filtered_urls
            
            if not img_urls:
                print("✗ No images or videos found on this page.")
                return
            
            # Count images vs videos
            video_count = len([u for u in img_urls if self.is_video_url(u)])
            image_count = len(img_urls) - video_count
            
            print(f"✓ Found {len(img_urls)} files ({image_count} images, {video_count} videos)")
            
            # Display sample
            print("\nSample of found files:")
            for i, img_url in enumerate(list(img_urls)[:5], 1):
                file_type = "VIDEO" if self.is_video_url(img_url) else "IMAGE"
                print(f"  {i}. [{file_type}] {os.path.basename(img_url)[:45]}...")
            if len(img_urls) > 5:
                print(f"  ... and {len(img_urls) - 5} more")
            
            # Filename settings
            print("\n" + "="*60)
            print("FILENAME SETTINGS")
            print("="*60)
            
            # Suggest prefix based on URL
            suggested_prefix = ""
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            if path_parts:
                last_part = path_parts[-1]
                if last_part and not last_part.isdigit():
                    suggested_prefix = last_part + '_'
            
            print(f"\nSuggested prefix: '{suggested_prefix}' (based on URL)")
            prefix = input(f"Enter filename prefix (press Enter for '{suggested_prefix}'): ").strip()
            
            if not prefix and suggested_prefix:
                prefix = suggested_prefix
            
            # Overwrite option
            print("\nOverwrite existing files?")
            overwrite = input("(y)es, (n)o (skip), (a)uto-rename: ").strip().lower()
            if overwrite not in ['y', 'n', 'a']:
                overwrite = 'a'
            
            # Small video filtering option
            skip_small_videos = False
            min_video_size_mb = 1.0
            
            if video_count > 0:
                print("\nSmall video filtering:")
                print("Small videos (< 1 MB) are often previews/thumbnails, not full videos.")
                filter_choice = input("Skip videos smaller than 1 MB? (y/n, default: y): ").strip().lower()
                
                if filter_choice == '' or filter_choice == 'y' or filter_choice == 'yes':
                    skip_small_videos = True
                    custom_size = input("Custom minimum size in MB? (press Enter for 1 MB): ").strip()
                    if custom_size:
                        try:
                            min_video_size_mb = float(custom_size)
                            print(f"✓ Will skip videos smaller than {min_video_size_mb} MB")
                        except:
                            min_video_size_mb = 1.0
                            print(f"✓ Using default: 1 MB")
                    else:
                        print(f"✓ Will skip videos smaller than 1 MB")
            
            # Confirm
            print(f"\n{'-'*60}")
            proceed = input(f"Download {len(img_urls)} files ({image_count} images, {video_count} videos)? (y/n): ").strip().lower()
            if proceed not in ['y', 'yes']:
                print("Download cancelled.")
                return
            
            # Download
            successful = 0
            skipped = 0
            failed = 0
            skipped_small_videos = 0
            
            print(f"\n{'='*60}")
            print("DOWNLOADING FILES")
            print('='*60)
            
            # Create subfolder
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            gallery_name = "gallery"
            if path_parts and path_parts[-1]:
                gallery_name = path_parts[-1]
            
            download_subfolder = os.path.join(self.download_path, f"{gallery_name}_{timestamp}")
            if not os.path.exists(download_subfolder):
                os.makedirs(download_subfolder)
            
            for i, img_url in enumerate(sorted(img_urls), 1):
                # Detect if URL is a video
                is_video = self.is_video_url(img_url)
                file_type = "VIDEO" if is_video else "IMAGE"
                
                # Check file size for videos if filtering is enabled
                if is_video and skip_small_videos:
                    try:
                        # Quick HEAD request to check file size
                        head_response = self.session.head(img_url, headers=self.headers, timeout=10, allow_redirects=True)
                        content_length = head_response.headers.get('content-length')
                        
                        if content_length:
                            file_size_bytes = int(content_length)
                            file_size_mb = file_size_bytes / (1024 * 1024)
                            
                            if file_size_mb < min_video_size_mb:
                                print(f"[{i}/{len(img_urls)}] [VIDEO] Skipping: {os.path.basename(urlparse(img_url).path)[:35]}...")
                                print(f"  ⊘ Too small ({file_size_mb:.2f} MB < {min_video_size_mb} MB minimum)")
                                skipped_small_videos += 1
                                continue
                    except:
                        # If we can't check size, proceed with download
                        pass
                
                if prefix:
                    filename = self.get_prefixed_filename(img_url, i, prefix, is_video)
                else:
                    filename = os.path.basename(urlparse(img_url).path)
                    if not filename or '.' not in filename:
                        # Try to determine if it's a video URL
                        if is_video:
                            filename = f'video_{i:04d}.mp4'
                        else:
                            filename = f'image_{i:04d}.jpg'
                
                save_path = os.path.join(download_subfolder, filename)
                
                # Check if exists
                if os.path.exists(save_path):
                    if overwrite == 'n':
                        print(f"[{i}/{len(img_urls)}] [{file_type}] Skipped (exists): {filename[:35]}...")
                        skipped += 1
                        continue
                    elif overwrite == 'a':
                        base_name, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(save_path):
                            filename = f"{base_name}_{counter}{ext}"
                            save_path = os.path.join(download_subfolder, filename)
                            counter += 1
                
                try:
                    print(f"[{i}/{len(img_urls)}] [{file_type}] Downloading: {filename[:35]}...")
                    
                    # Add special headers for token-based video URLs
                    download_headers = self.headers.copy()
                    
                    # If URL is from an embed source, add referer from the original page
                    parsed_url = urlparse(img_url)
                    if 'get_file' in img_url or 'v-acctoken' in img_url or 'token' in img_url.lower():
                        # For token-based URLs, add referer and origin
                        embed_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        download_headers['Referer'] = url  # Original page URL
                        download_headers['Origin'] = embed_domain
                        print(f"  → Using referer: {url[:50]}...")
                    
                    # Download with retry
                    for attempt in range(2):
                        try:
                            img_response = self.session.get(img_url, headers=download_headers, 
                                                          stream=True, timeout=60)  # Increased timeout for videos
                            img_response.raise_for_status()
                            break
                        except requests.exceptions.Timeout:
                            if attempt == 0:
                                print(f"  Timeout, retrying...")
                                time.sleep(1)
                                continue
                            else:
                                raise
                    
                    # Download
                    with open(save_path, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    actual_size = os.path.getsize(save_path)
                    
                    # Videos can be larger, so only flag very small files
                    min_size = 1024 if not is_video else 10240  # 1KB for images, 10KB for videos
                    if actual_size < min_size:
                        print(f"  ⚠ File very small ({actual_size} bytes), may not be valid")
                        os.remove(save_path)
                        failed += 1
                    else:
                        size_kb = actual_size / 1024
                        if size_kb > 1024:
                            print(f"  ✓ Saved ({size_kb/1024:.2f} MB)")
                        else:
                            print(f"  ✓ Saved ({size_kb:.1f} KB)")
                        
                        # Warn if video is suspiciously small (but above minimum filter)
                        if is_video and actual_size < 5 * 1024 * 1024:  # Less than 5 MB
                            if not skip_small_videos or actual_size >= min_video_size_mb * 1024 * 1024:
                                print(f"     ⚠ Warning: Video is relatively small, may be low quality or preview")
                        
                        successful += 1
                    
                except Exception as e:
                    error_msg = str(e)
                    error_type = type(e).__name__
                    
                    # Try to get HTTP status code if available
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        print(f"  ✗ Failed: HTTP {status_code} ({error_type})")
                        
                        # Give hints based on status code
                        if status_code == 403:
                            print(f"     → Likely: Access token expired or invalid")
                        elif status_code == 404:
                            print(f"     → Likely: File not found or URL expired")
                        elif status_code == 401:
                            print(f"     → Likely: Authentication required")
                    else:
                        print(f"  ✗ Failed: {error_type}")
                    
                    failed += 1
                
                if i < len(img_urls):
                    time.sleep(0.2)
            
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print('='*60)
            print(f"Total files found: {len(img_urls)} ({image_count} images, {video_count} videos)")
            print(f"Successfully downloaded: {successful}")
            print(f"Skipped (already existed): {skipped}")
            if skipped_small_videos > 0:
                print(f"Skipped (small videos < {min_video_size_mb} MB): {skipped_small_videos}")
            print(f"Failed: {failed}")
            print(f"Location: {download_subfolder}")
            
            if successful > 0:
                print(f"\n✓ Download successful!")
                try:
                    if sys.platform == 'win32':
                        os.startfile(download_subfolder)
                except:
                    pass
            else:
                print(f"\n✗ No images were downloaded successfully.")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error accessing page: {e}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Scraper (Bunkr + Pixeldrain + Simpcity Forums + Generic Galleries)')
    parser.add_argument('url', nargs='?', help='Album, file, forum thread, or gallery URL')
    parser.add_argument('-o', '--output', default='downloads', help='Output directory')
    parser.add_argument('-r', '--rate', type=int, default=5, help='Rate limit (seconds)')
    parser.add_argument('-k', '--key', help='Pixeldrain API key (or set PIXELDRAIN_API_KEY env var)')
    parser.add_argument('--mode', choices=['auto', 'bunkr', 'pixeldrain', 'forum', 'gallery'], default='auto',
                       help='Force a specific scraper mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for forum scraper')
    
    args = parser.parse_args()
    
    # Create cookies directory at startup (for forum scraper)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_dir = os.path.join(script_dir, 'cookies')
    if not os.path.exists(cookies_dir):
        os.makedirs(cookies_dir)
        print(f"✓ Created cookies directory: {cookies_dir}\n")
    
    print("=" * 70)
    print("UNIVERSAL SCRAPER")
    print("Supports: Bunkr, Pixeldrain, Simpcity Forums, Generic Galleries")
    print("=" * 70)
    print()
    
    # Interactive mode if no URL provided
    if not args.url:
        print("Choose scraper mode:")
        print("1. Bunkr album/file")
        print("2. Pixeldrain album/file")
        print("3. Simpcity forum thread")
        print("4. Generic gallery (viralthots.tv, etc.)")
        print("5. Auto-detect from URL")
        
        mode_choice = input("\nChoose option (1/2/3/4/5): ").strip()
        
        url = input("Enter URL: ").strip()
        
        if mode_choice == '1':
            args.mode = 'bunkr'
        elif mode_choice == '2':
            args.mode = 'pixeldrain'
        elif mode_choice == '3':
            args.mode = 'forum'
        elif mode_choice == '4':
            args.mode = 'gallery'
        else:
            args.mode = 'auto'
        
        args.url = url
    
    # Auto-detect mode if not specified
    if args.mode == 'auto':
        url_lower = args.url.lower()
        if 'simpcity' in url_lower or '/threads/' in url_lower:
            args.mode = 'forum'
        elif 'pixeldrain' in url_lower:
            args.mode = 'pixeldrain'
        elif 'bunkr' in url_lower:
            args.mode = 'bunkr'
        elif any(keyword in url_lower for keyword in ['viralthots', 'album', 'gallery', 'photos', 'video']):
            args.mode = 'gallery'
        else:
            # Try to detect from URL structure
            if '/threads/' in args.url or '/forums/' in args.url:
                args.mode = 'forum'
            elif '/album/' in args.url or '/gallery/' in args.url or '/video/' in args.url:
                args.mode = 'gallery'
            else:
                print("⚠ Could not auto-detect mode. Defaulting to generic gallery scraper.")
                args.mode = 'gallery'
    
    # Run appropriate scraper
    if args.mode == 'forum':
        print("🔧 Mode: Simpcity Forum Scraper\n")
        downloader = ForumImageDownloader(output_dir=args.output, debug_mode=args.debug)
        downloader.download_images(args.url)
    elif args.mode == 'gallery':
        print("🔧 Mode: Generic Gallery Scraper\n")
        downloader = GenericGalleryDownloader(output_dir=args.output)
        downloader.download_images(args.url)
    else:
        print(f"🔧 Mode: Bunkr/Pixeldrain Scraper\n")
        scraper = UniversalScraper(
            output_dir=args.output, 
            rate_limit=args.rate,
            pixeldrain_api_key=args.key
        )
        await scraper.scrape(args.url)
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
