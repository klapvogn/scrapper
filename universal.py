#!/usr/bin/env python3
"""
Universal Scraper for Bunkr, Pixeldrain, and Simpcity Forums, viralthots.tv, coomer.st, Fapello, Pixhost, Kemono

Requires: pip install playwright aiohttp beautifulsoup4 tqdm aiofiles requests pillow

Do the below AFTER you have installed the ABOVE

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
            self.pixeldrain_api_key = os.getenv('25a95570-0238-4b69-ad06-1303c6a31c48')
        
        # Don't print API key status here - will print only when scraping Pixeldrain
        
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
            # Show API key status only when actually scraping Pixeldrain
            if self.pixeldrain_api_key:
                print(f"🔑 Using Pixeldrain API key")
            
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
        # Show API key status only when actually scraping Pixeldrain
        if self.pixeldrain_api_key:
            print(f"🔑 Using Pixeldrain API key: {self.pixeldrain_api_key[:8]}...")
        else:
            print("ℹ️  No Pixeldrain API key (public access only)")        
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
                        (96, 96), (48, 48), (50, 62), (192, 192),  (300, 100),
                        (64, 64), (128, 128), (32, 32), (112, 112), (1200, 1200), (1024, 1024),
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
            r'50x62', r'96x96', r'192x192', r'300x100', r'48x48', r'300x100', r'1200x1200',
            r'32x32', r'64x64', r'128x128', r'150x150', r'1024x1024',
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
                # Check for /page-N format (with dash) - e.g., /page-4
                dash_match = re.search(r'/page-(\d+)(?:/|$)', url, re.IGNORECASE)
                if dash_match:
                    page_num = int(dash_match.group(1))
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
    
    def extract_main_video_only(self, html_content, base_url):
        """Extract only the main video from a single video page (not thumbnails from 'More Videos')"""
        video_urls = set()
        
        # PRIORITY 1: Main video player sources (these are the actual video files)
        main_video_patterns = [
            # HTML5 video tags in the main player
            r"<video[^>]+src=[\"'](https?://[^\"']+)[\"']",
            r"<source[^>]+src=[\"'](https?://[^\"']+\.(?:mp4|webm|mov|avi|mkv))[\"']",
            # Video URLs in JavaScript player configs
            r"video_url\s*[:=]\s*[\"']([^\"']+\.(?:mp4|webm|mov))[\"']",
            r"source\s*[:=]\s*[\"']([^\"']+\.(?:mp4|webm|mov))[\"']",
            r"file\s*[:=]\s*[\"']([^\"']+\.(?:mp4|webm|mov))[\"']",
            # JSON-style video configs
            r'"url"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
            r'"source"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
            r'"file"\s*:\s*"([^"]+\.(?:mp4|webm|mov))"',
        ]
        
        for pattern in main_video_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 15 and not match.startswith('data:'):
                    # Normalize URL
                    if match.startswith('//'):
                        match = 'https:' + match
                    elif match.startswith('/'):
                        match = urljoin(base_url, match)
                    
                    # Skip player scripts and thumbnails
                    if not any(skip in match.lower() for skip in ['player.js', 'analytics', 'ads', '.js', '.css', 'thumb', 'preview']):
                        video_urls.add(match)
        
        # PRIORITY 2: Check iframe embeds for video
        if not video_urls:
            iframe_videos = self.extract_from_embed_pages(html_content, base_url)
            video_urls.update(iframe_videos)
        
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
            
            # Check if it's a SINGLE VIDEO page (not gallery)
            is_single_video = '/video/' in url.lower()
            
            if is_single_video:
                print("✓ Detected single video page - extracting main video only (no thumbnails)...")
                img_urls = self.extract_main_video_only(response.text, url)
            else:
                # Check if it's a gallery or video site
                is_gallery = any(keyword in url.lower() for keyword in 
                               ['viralthots.tv', 'album', 'gallery', 'photos'])
                
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

class CoomerScraper:
    """Scraper for coomer.st using Playwright to render the page"""
    
    def __init__(self, output_dir: str = "downloads"):
        self.session = requests.Session()
        self.download_path = output_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://coomer.st/',
        }
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        if self.browser:
            return
        
        print("🌐 Starting browser...")
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
    
    async def close_browser(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def get_rendered_page(self, url, max_retries=3):
        """Get fully rendered page content with retry logic"""
        if not self.browser:
            await self.init_browser()
        
        page = await self.context.new_page()
        
        for attempt in range(max_retries):
            try:
                # Increased timeout to 60 seconds
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Wait for React to render content
                await page.wait_for_selector('article, .post, [class*="card"]', timeout=20000)
                
                # Additional wait for dynamic content
                await asyncio.sleep(2)
                
                # Get the rendered HTML
                html_content = await page.content()
                
                await page.close()
                return html_content
                
            except Exception as e:
                error_type = type(e).__name__
                
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s
                    print(f"  ✗ {error_type} (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                    
                    # Close the failed page
                    try:
                        await page.close()
                    except:
                        pass
                    
                    # Create new page for retry
                    page = await self.context.new_page()
                    
                    await asyncio.sleep(wait_time)
                else:
                    print(f"  ✗ {error_type} - all {max_retries} attempts failed")
                    try:
                        await page.close()
                    except:
                        pass
                    return None
        
        return None
    
    def extract_pagination_info(self, html_content):
        """Extract pagination information from profile page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for pagination info in the page
        # Common pattern: "Showing 1 - 50 of 495"
        pagination_text = soup.get_text()
        
        # Extract total count
        match = re.search(r'Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)', pagination_text, re.IGNORECASE)
        if match:
            total_posts = int(match.group(1))
            return total_posts
        
        return None
    
    def extract_post_links_from_html(self, html_content, base_url):
        """Extract post links from rendered HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        post_links = []
        
        # Find all links that contain "/post/"
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/post/' in href:
                # Convert to absolute URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    parsed = urlparse(base_url)
                    full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                else:
                    full_url = urljoin(base_url, href)
                
                if full_url not in post_links:
                    post_links.append(full_url)
        
        return post_links
    
    async def get_all_post_links(self, profile_url):
        """Get ALL post links from profile by following pagination"""
        print("🔍 Loading profile page...")
        
        # Get first page
        html_content = await self.get_rendered_page(profile_url)
        
        if not html_content:
            print("✗ Could not load profile page")
            return []
        
        # Extract total posts count
        total_posts = self.extract_pagination_info(html_content)
        
        if total_posts:
            print(f"📊 Profile has {total_posts} total posts")
        
        # Extract posts from first page
        all_post_links = self.extract_post_links_from_html(html_content, profile_url)
        print(f"✓ Extracted {len(all_post_links)} posts from page 1")
        
        # If we have total count, calculate pages needed
        if total_posts and total_posts > 50:
            pages_needed = (total_posts + 49) // 50  # Round up
            print(f"📄 Need to scrape {pages_needed} pages total")
            
            # Coomer.st uses ?o=offset for pagination (o=50, o=100, etc.)
            for page_num in range(2, pages_needed + 1):
                offset = (page_num - 1) * 50
                paginated_url = f"{profile_url}?o={offset}"
                
                print(f"  → Loading page {page_num}/{pages_needed} (offset {offset})...")
                
                page_html = await self.get_rendered_page(paginated_url)
                
                if page_html:
                    page_posts = self.extract_post_links_from_html(page_html, profile_url)
                    
                    # Add only new posts (avoid duplicates)
                    new_posts = [p for p in page_posts if p not in all_post_links]
                    all_post_links.extend(new_posts)
                    
                    print(f"    ✓ Found {len(new_posts)} new posts (total: {len(all_post_links)})")
                    
                    # If we got no new posts, we've reached the end
                    if len(new_posts) == 0:
                        print(f"    ℹ No more new posts, stopping pagination")
                        break
                else:
                    print(f"    ✗ Failed to load page {page_num} after all retries")
                    print(f"    ⚠ Continuing with remaining pages...")
                    # Don't stop entirely, continue to next page
                
                # Rate limiting between pages
                await asyncio.sleep(2)
        
        # Summary of pagination
        if total_posts:
            missing = total_posts - len(all_post_links)
            if missing > 0:
                print(f"\n⚠ WARNING: Expected {total_posts} posts but found {len(all_post_links)}")
                print(f"   Missing {missing} posts (likely due to failed page loads)")
                print(f"   You can re-run the script later to get the missing posts")
        
        return all_post_links
    
    def extract_media_from_html(self, html_content, base_url):
        """Extract media URLs from rendered post HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        media_urls = set()
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Pattern 1: All links with /data/ in them
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/data/' in href:
                if href.startswith('http'):
                    media_urls.add(href)
                elif href.startswith('/'):
                    media_urls.add(f"{base_domain}{href}")
        
        # Pattern 2: Image tags with /data/ or /thumbnail/
        for img in soup.find_all('img', src=True):
            src = img['src']
            if '/data/' in src or '/thumbnail/' in src:
                # Convert thumbnail to full URL
                if '/thumbnail/data/' in src:
                    src = src.replace('/thumbnail/data/', '/data/')
                
                if src.startswith('http'):
                    media_urls.add(src)
                elif src.startswith('/'):
                    media_urls.add(f"{base_domain}{src}")
        
        # Pattern 3: Video/source tags
        for video in soup.find_all(['video', 'source'], src=True):
            src = video['src']
            if src.startswith('http'):
                media_urls.add(src)
            elif src.startswith('/'):
                media_urls.add(f"{base_domain}{src}")
        
        # Pattern 4: Look for any coomer.st/data/ URLs in the HTML
        data_pattern = r'(https?://(?:coomer\.st|coomer\.party|coomer\.su)/data/[^\s\'"<>]+)'
        matches = re.findall(data_pattern, html_content, re.IGNORECASE)
        media_urls.update(matches)
        
        return list(media_urls)
    
    async def download_single_post(self, post_url, user_folder):
        """Download all media from a single post"""
        if not self.browser:
            await self.init_browser()
        
        page = await self.context.new_page()
        failed_urls = []
        
        try:
            await page.goto(post_url, wait_until='networkidle', timeout=30000)
            
            try:
                await page.wait_for_selector('img[src*="/data/"], a[href*="/data/"], video', timeout=10000)
            except:
                await asyncio.sleep(3)
            
            html_content = await page.content()
            await page.close()
            
            media_urls = self.extract_media_from_html(html_content, post_url)
            
            if not media_urls:
                return 0, 0, []
            
            # DEDUPLICATE by file hash
            seen_hashes = set()
            unique_urls = []
            
            for url in media_urls:
                hash_match = re.search(r'/([a-f0-9]{32,})', url, re.IGNORECASE)
                if hash_match:
                    file_hash = hash_match.group(1)
                    if file_hash not in seen_hashes:
                        seen_hashes.add(file_hash)
                        unique_urls.append(url)
                else:
                    unique_urls.append(url)
            
            if len(unique_urls) < len(media_urls):
                duplicates_removed = len(media_urls) - len(unique_urls)
                if duplicates_removed > 0:
                    print(f"  ℹ Removed {duplicates_removed} duplicate(s)")
            
            media_urls = unique_urls
            
            if not media_urls:
                return 0, 0, []
            
            video_count = len([u for u in media_urls if any(ext in u.lower() for ext in ['.mp4', '.webm'])])
            image_count = len(media_urls) - video_count
            
            print(f"  ✓ Found {len(media_urls)} unique files ({image_count} images, {video_count} videos)")
            
            successful = 0
            failed = 0
            skipped_small = 0
            
            for i, media_url in enumerate(media_urls, 1):
                is_video = any(ext in media_url.lower() for ext in ['.mp4', '.webm'])
                file_type = "VIDEO" if is_video else "IMAGE"
                
                filename = os.path.basename(urlparse(media_url).path)
                if not filename or len(filename) < 5:
                    ext = '.mp4' if is_video else '.jpg'
                    filename = f"file_{i:03d}{ext}"
                
                save_path = os.path.join(user_folder, filename)
                
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    print(f"    [{i}/{len(media_urls)}] [{file_type}] ⊙ Exists: {filename[:35]}...")
                    successful += 1
                    continue
                
                max_retries = 5
                retry_delay = 3
                download_failed = True
                
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            print(f"    [{i}/{len(media_urls)}] [{file_type}] Retry {attempt}/{max_retries-1}: {filename[:35]}...")
                        else:
                            print(f"    [{i}/{len(media_urls)}] [{file_type}] Downloading: {filename[:35]}...")
                        
                        timeout_duration = 180 if is_video else 90
                        
                        response = self.session.get(
                            media_url, 
                            headers=self.headers, 
                            stream=True, 
                            timeout=timeout_duration
                        )
                        
                        if response.status_code in [500, 503]:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)
                                print(f"      ✗ HTTP {response.status_code} (waiting {wait_time}s...)")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                print(f"      ✗ HTTP {response.status_code} (exhausted retries)")
                                failed += 1
                                failed_urls.append((media_url, filename, f"HTTP {response.status_code}"))
                                break
                        
                        response.raise_for_status()
                        
                        # Get file size for progress bar
                        total_size = int(response.headers.get('content-length', 0))
                        
                        # Show progress bar for files larger than 10 MB
                        show_progress = total_size > 10 * 1024 * 1024
                        
                        if show_progress:
                            # Create progress bar
                            pbar = tqdm(
                                total=total_size,
                                unit='B',
                                unit_scale=True,
                                unit_divisor=1024,
                                desc=f"      ⬇ {filename[:30]}",
                                leave=False,
                                ncols=80
                            )
                            
                            with open(save_path, 'wb') as f:
                                downloaded = 0
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        pbar.update(len(chunk))
                            
                            pbar.close()
                        else:
                            # No progress bar for small files
                            with open(save_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                        
                        actual_size = os.path.getsize(save_path)
                        
                        min_size = 1024 if is_video else 51200
                        
                        if actual_size < min_size:
                            size_kb = actual_size / 1024
                            print(f"      ✗ Too small ({size_kb:.1f} KB)")
                            os.remove(save_path)
                            failed += 1
                            skipped_small += 1
                            failed_urls.append((media_url, filename, f"Too small: {size_kb:.1f} KB"))
                        else:
                            size_kb = actual_size / 1024
                            if size_kb > 1024:
                                print(f"      ✓ Downloaded ({size_kb/1024:.2f} MB)")
                            else:
                                print(f"      ✓ Downloaded ({size_kb:.1f} KB)")
                            successful += 1
                            download_failed = False
                        
                        break
                        
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"      ✗ Timeout (waiting {wait_time}s...)")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"      ✗ Timeout (exhausted retries)")
                            failed += 1
                            failed_urls.append((media_url, filename, "Timeout"))
                            
                    except requests.exceptions.HTTPError as e:
                        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"      ✗ HTTP {status_code} (waiting {wait_time}s...)")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"      ✗ HTTP {status_code} (exhausted retries)")
                            failed += 1
                            failed_urls.append((media_url, filename, f"HTTP {status_code}"))
                        
                    except Exception as e:
                        error_name = type(e).__name__
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"      ✗ {error_name} (waiting {wait_time}s...)")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"      ✗ {error_name} (exhausted retries)")
                            failed += 1
                            failed_urls.append((media_url, filename, error_name))
                
                import random
                base_delay = 1.5 if not is_video else 2.5
                jitter = random.uniform(0, 0.5)
                await asyncio.sleep(base_delay + jitter)
            
            if skipped_small > 0:
                print(f"  ℹ Skipped {skipped_small} file(s) < 50 KB")
            
            return successful, failed, failed_urls
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            try:
                await page.close()
            except:
                pass
            return 0, 1, []
    
    async def download_user_profile_async(self, url):
        """Download all posts from user profile (async version)"""
        print(f"\n📥 Scraping coomer.st user profile: {url}")
        print("-" * 60)
        
        try:
            # Extract username
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            service = path_parts[0] if len(path_parts) > 0 else 'onlyfans'
            username = path_parts[2] if len(path_parts) > 2 else 'unknown'
            
            print(f"Service: {service}")
            print(f"User: {username}")
            print()
            
            # Get ALL post links with pagination
            post_links = await self.get_all_post_links(url)
            
            if not post_links:
                print("✗ No posts found on this profile")
                print("\nThis could mean:")
                print("  • The profile has no posts")
                print("  • The page structure has changed")
                print("  • Posts are loaded via infinite scroll (need to scroll down)")
                return
            
            print(f"\n✓ Total posts found: {len(post_links)}")
            
            # Show sample
            print("\nSample posts:")
            for i, link in enumerate(post_links[:10], 1):
                post_id = link.split('/post/')[-1].split('?')[0] if '/post/' in link else 'unknown'
                print(f"  {i}. Post {post_id}")
            if len(post_links) > 10:
                print(f"  ... and {len(post_links) - 10} more")
            
            # Ask user
            print(f"\n{'='*60}")
            print("DOWNLOAD OPTIONS")
            print('='*60)
            print(f"1. Download ALL {len(post_links)} posts")
            print(f"2. Download first N posts")
            print(f"3. Download specific range (e.g., 1-100)")
            print(f"4. Cancel")
            
            choice = input("\nChoose option (1/2/3/4): ").strip()
            
            if choice == '4':
                print("Download cancelled.")
                return
            elif choice == '2':
                try:
                    n = int(input(f"How many posts? (1-{len(post_links)}): ").strip())
                    post_links = post_links[:n]
                    print(f"✓ Will download first {len(post_links)} posts")
                except:
                    print("Invalid, downloading all.")
            elif choice == '3':
                try:
                    range_input = input("Enter range (e.g., 1-100 or 50-150): ").strip()
                    if '-' in range_input:
                        start, end = map(int, range_input.split('-'))
                        start = max(1, start) - 1  # Convert to 0-indexed
                        end = min(len(post_links), end)
                        post_links = post_links[start:end]
                        print(f"✓ Will download posts {start+1} to {end}")
                except:
                    print("Invalid range, downloading all.")
            else:
                print(f"✓ Will download all {len(post_links)} posts")
            
            # Create folder
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            user_folder = os.path.join(self.download_path, f"coomer_{service}_{username}_{timestamp}")
            os.makedirs(user_folder, exist_ok=True)
            
            # Download each post
            print(f"\n{'='*60}")
            print("DOWNLOADING POSTS")
            print('='*60)
            
            total_files = 0
            total_failed = 0
            all_failed_urls = []  # ← ADD THIS: Collect all failed URLs
            
            for i, post_url in enumerate(post_links, 1):
                post_id = post_url.split('/post/')[-1].split('?')[0] if '/post/' in post_url else f'{i}'
                print(f"\n[{i}/{len(post_links)}] Post {post_id}:")
                
                successful, failed, failed_urls = await self.download_single_post(post_url, user_folder)  # ← CHANGE
                total_files += successful
                total_failed += failed
                
                # ← ADD: Collect failed URLs from this post
                if failed_urls:
                    for url, filename, error in failed_urls:
                        all_failed_urls.append((post_id, url, filename, error))
                
                await asyncio.sleep(1)
            
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print('='*60)
            print(f"User: {username}")
            print(f"Service: {service}")
            print(f"Total posts processed: {len(post_links)}")
            print(f"Total files downloaded: {total_files}")
            print(f"Total files failed: {total_failed}")
            print(f"Location: {user_folder}")
            
            if total_files > 0:
                print(f"\n✓ Download successful!")
                try:
                    if sys.platform == 'win32':
                        os.startfile(user_folder)
                except:
                    pass
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print('='*60)
            print(f"User: {username}")
            print(f"Service: {service}")
            print(f"Total posts processed: {len(post_links)}")
            print(f"Total files downloaded: {total_files}")
            print(f"Total files failed: {total_failed}")
            print(f"Location: {user_folder}")
            
            # ← ADD THIS ENTIRE SECTION
            # Save failed URLs to file
            if all_failed_urls:
                failed_log = os.path.join(user_folder, "failed_downloads.txt")
                with open(failed_log, 'w', encoding='utf-8') as f:
                    f.write(f"Failed Downloads from {username} ({service})\n")
                    f.write(f"Downloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total failed: {len(all_failed_urls)}\n")
                    f.write("="*80 + "\n\n")
                    
                    for post_id, url, filename, error in all_failed_urls:
                        f.write(f"Post: {post_id}\n")
                        f.write(f"Filename: {filename}\n")
                        f.write(f"Error: {error}\n")
                        f.write(f"URL: {url}\n")
                        f.write("-"*80 + "\n")
                
                print(f"\n⚠ {total_failed} files failed - saved to: failed_downloads.txt")
                print(f"   You can retry these URLs individually later")
            
            if total_files > 0:
                print(f"\n✓ Download successful!")
                try:
                    if sys.platform == 'win32':
                        os.startfile(user_folder)
                except:
                    pass                
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()
    
    async def scrape(self, url):
        """Main entry point (async)"""
        await self.download_user_profile_async(url)

class FapelloScraper:
    """Scraper for fapello.com profiles using Playwright"""
    
    def __init__(self, output_dir: str = "downloads"):
        self.session = requests.Session()
        self.download_path = output_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://fapello.com/',
        }
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        if self.browser:
            return
        
        print("🌐 Starting browser...")
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
    
    async def close_browser(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def scroll_to_load_all(self, page, max_scrolls=100):
        """Scroll page to load all images via infinite scroll"""
        print("  Scrolling to load all images...")
        
        previous_height = 0
        scroll_count = 0
        no_change_count = 0
        
        while scroll_count < max_scrolls:
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)  # Wait for images to load
            
            # Get new height
            current_height = await page.evaluate('document.body.scrollHeight')
            
            if current_height == previous_height:
                no_change_count += 1
                if no_change_count >= 3:  # No change for 3 scrolls = done
                    print(f"  ✓ Reached end after {scroll_count} scrolls")
                    break
            else:
                no_change_count = 0
            
            previous_height = current_height
            scroll_count += 1
            
            if scroll_count % 10 == 0:
                print(f"  → Scrolled {scroll_count} times...")
        
        # Scroll back to top to ensure all images are in DOM
        await page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(1)
    
    def extract_profile_images(self, html_content, username):
        """Extract all image URLs from profile with comprehensive patterns"""
        soup = BeautifulSoup(html_content, 'html.parser')
        img_urls = set()
        
        print("  🔍 Analyzing page structure...")
        
        # DEBUG: Save HTML to file for inspection
        debug_file = os.path.join(self.download_path, f"debug_{username}.html")
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  💾 Saved HTML to: {debug_file}")
        
        # Strategy 1: Find ALL image URLs in the page
        all_image_patterns = [
            r'(https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'<>]*)?)',
            r'(//[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s"\'<>]*)?)',
        ]
        
        for pattern in all_image_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('//'):
                    match = 'https:' + match
                img_urls.add(match)
        
        print(f"  → Found {len(img_urls)} total image URLs in HTML")
        
        # Strategy 2: Extract from img tags
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-original', 'data-lazy']:
                url = img.get(attr, '')
                if url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://fapello.com' + url
                    img_urls.add(url)
        
        # Strategy 3: Extract from links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://fapello.com' + href
                img_urls.add(href)
        
        print(f"  → Total URLs collected: {len(img_urls)}")
        
        # NOW FILTER: Only keep images from this profile
        filtered_urls = []
        
        # Analyze URL patterns
        url_samples = list(img_urls)[:20]
        print(f"\n  📋 Sample URLs found:")
        for i, url in enumerate(url_samples[:10], 1):
            print(f"     {i}. {url[:80]}...")
        
        # Detect the URL pattern for this profile's images
        # Common patterns:
        # - /content/username/####/filename.jpg
        # - /images/username/filename.jpg  
        # - /i/username_####.jpg
        # - Contains username in path
        
        for url in img_urls:
            url_lower = url.lower()
            filename = os.path.basename(urlparse(url).path).lower()
            
            # Skip obvious UI elements
            skip_keywords = ['button', 'logo', 'icon', 'banner', 'ad', 'welcome', 
                           'camsoda', 'porndude', 'avatar', 'header', 'footer',
                           'sponsor', 'promo', 'badge']
            if any(keyword in filename for keyword in skip_keywords):
                continue
            
            # Skip tiny images (UI elements are usually small)
            if any(size in url_lower for size in ['_50x50', '_100x100', '_150x150', '50px', '100px']):
                continue
            
            # Accept if URL contains username OR if it's from certain directories
            if username.lower() in url_lower:
                filtered_urls.append(url)
            elif any(path in url_lower for path in ['/content/', '/images/', '/media/', '/i/']):
                # Only accept from content directories if it looks like a real image
                if '_' in filename or any(c.isdigit() for c in filename):
                    # Check if it's NOT from another profile
                    # Extract potential username from URL
                    url_parts = url.lower().split('/')
                    is_other_profile = False
                    for part in url_parts:
                        if part and part != username.lower() and len(part) > 3:
                            # If this part looks like another username, skip
                            if not part.isdigit() and part not in ['content', 'images', 'media', 'i', 'www', 'fapello.com']:
                                # This might be another profile name
                                # Only skip if we're confident
                                if '_' in filename and part in filename:
                                    is_other_profile = True
                                    break
                    
                    if not is_other_profile:
                        filtered_urls.append(url)
        
        print(f"  → After filtering: {len(filtered_urls)} profile images")
        
        # Remove duplicates and thumbnails
        final_urls = set()
        for url in filtered_urls:
            # Convert thumbnail URLs to full-size
            full_url = url.replace('_300px.', '.').replace('_thumb.', '.').replace('_small.', '.')
            final_urls.add(full_url)
        
        print(f"  → Final count (deduplicated): {len(final_urls)}")
        
        # Show sample of what we're keeping
        if final_urls:
            print(f"\n  ✓ Sample of images to download:")
            for i, url in enumerate(list(final_urls)[:5], 1):
                print(f"     {i}. {os.path.basename(url)[:60]}...")
        
        return list(final_urls)
    
    async def download_images_async(self, profile_url):
        """Download all images from Fapello profile (async with browser)"""
        print(f"\n📥 Scraping Fapello profile: {profile_url}")
        print("-" * 60)
        
        try:
            # Extract username from URL
            parsed = urlparse(profile_url)
            username = parsed.path.strip('/').split('/')[-1]
            print(f"User: {username}\n")
            
            # Initialize browser
            await self.init_browser()
            
            # Open page
            print("🌐 Loading profile page...")
            page = await self.context.new_page()
            
            try:
                await page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for content to load
                await page.wait_for_selector('img, a[href*="jpg"]', timeout=10000)
                
                # Scroll to load all images
                await self.scroll_to_load_all(page, max_scrolls=150)
                
                # Get the fully rendered HTML
                html_content = await page.content()
                
                await page.close()
                
                # Extract images from this profile
                print("\n🔍 Extracting image URLs...")
                img_urls = self.extract_profile_images(html_content, username)
                
                if not img_urls:
                    print("\n✗ No images found for this profile")
                    print(f"\n💡 Debug tip: Check the saved HTML file to see the page structure")
                    print(f"   File: {os.path.join(self.download_path, f'debug_{username}.html')}")
                    return
                
                print(f"\n✓ Ready to download {len(img_urls)} images\n")
                
                # Ask for confirmation
                print(f"{'-'*60}")
                proceed = input(f"Download {len(img_urls)} images? (y/n): ").strip().lower()
                if proceed not in ['y', 'yes']:
                    print("Download cancelled.")
                    return
                
                # Create folder
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                download_folder = os.path.join(self.download_path, f"fapello_{username}_{timestamp}")
                os.makedirs(download_folder, exist_ok=True)
                
                # Download images
                print(f"\n{'='*60}")
                print("DOWNLOADING IMAGES")
                print('='*60)
                
                successful = 0
                failed = 0
                
                for i, img_url in enumerate(sorted(img_urls), 1):
                    filename = os.path.basename(urlparse(img_url).path)
                    
                    # Remove query parameters
                    if '?' in filename:
                        filename = filename.split('?')[0]
                    
                    if not filename or '.' not in filename:
                        filename = f"{username}_{i:04d}.jpg"
                    
                    save_path = os.path.join(download_folder, filename)
                    
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                        print(f"[{i}/{len(img_urls)}] ⊙ Exists: {filename[:45]}...")
                        successful += 1
                        continue
                    
                    try:
                        print(f"[{i}/{len(img_urls)}] Downloading: {filename[:45]}...", end=' ')
                        
                        # Download with retries
                        for attempt in range(3):
                            try:
                                img_response = self.session.get(img_url, headers=self.headers, 
                                                               stream=True, timeout=60)
                                img_response.raise_for_status()
                                break
                            except:
                                if attempt < 2:
                                    await asyncio.sleep(2)
                                    continue
                                else:
                                    raise
                        
                        with open(save_path, 'wb') as f:
                            for chunk in img_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        file_size = os.path.getsize(save_path)
                        
                        # Require at least 10KB for images
                        if file_size < 10240:
                            print(f"✗ Too small ({file_size/1024:.1f} KB)")
                            os.remove(save_path)
                            failed += 1
                        else:
                            size_kb = file_size / 1024
                            if size_kb > 1024:
                                print(f"✓ ({size_kb/1024:.2f} MB)")
                            else:
                                print(f"✓ ({size_kb:.1f} KB)")
                            successful += 1
                        
                    except Exception as e:
                        print(f"✗ {type(e).__name__}")
                        failed += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                
                # Summary
                print(f"\n{'='*60}")
                print("DOWNLOAD SUMMARY")
                print('='*60)
                print(f"User: {username}")
                print(f"Successfully downloaded: {successful}/{len(img_urls)}")
                print(f"Failed: {failed}/{len(img_urls)}")
                print(f"Location: {download_folder}")
                
                if successful > 0:
                    print(f"\n✓ Download complete!")
                    try:
                        if sys.platform == 'win32':
                            os.startfile(download_folder)
                    except:
                        pass
                
            except Exception as e:
                print(f"✗ Error loading page: {e}")
                try:
                    await page.close()
                except:
                    pass
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()
    
    async def scrape(self, url):
        """Main entry point (async)"""
        await self.download_images_async(url)

class PixhostScraper:
    """Scraper for pixhost.to galleries"""
    
    def __init__(self, output_dir: str = "downloads"):
        self.session = requests.Session()
        self.download_path = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://pixhost.to/',
        }
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    def extract_image_urls_from_gallery(self, html_content, base_url):
        """Extract full-size image URLs from Pixhost gallery page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        image_urls = []
        
        # Method 1: Look for direct image links in the gallery
        # Pixhost galleries often have <a> tags with href to /show/{id}
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/show/' in href:
                # Get the individual image page
                if not href.startswith('http'):
                    if href.startswith('/'):
                        href = f"https://pixhost.to{href}"
                    else:
                        href = urljoin(base_url, href)
                
                # Extract full image URL from individual page
                try:
                    response = self.session.get(href, headers=self.headers, timeout=15)
                    if response.status_code == 200:
                        # Look for the full-size image in the page
                        img_soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Try to find the main image (usually in an <img> tag with specific class/id)
                        # Pattern 1: Look for img with src containing 'pixhost.to/images/'
                        for img in img_soup.find_all('img'):
                            src = img.get('src', '')
                            if 'pixhost.to/images/' in src or 'img' in urlparse(src).netloc:
                                if src.startswith('//'):
                                    src = 'https:' + src
                                image_urls.append(src)
                                break
                        
                        # Pattern 2: Look for direct links to images
                        if not any('pixhost.to/images/' in url for url in image_urls[-1:]):
                            for link2 in img_soup.find_all('a', href=True):
                                href2 = link2['href']
                                if any(ext in href2.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                                    if href2.startswith('//'):
                                        href2 = 'https:' + href2
                                    image_urls.append(href2)
                                    break
                    
                    time.sleep(0.3)  # Rate limiting
                    
                except Exception as e:
                    print(f"  ⚠ Failed to get image from {href}: {e}")
                    continue
        
        # Remove duplicates
        image_urls = list(dict.fromkeys(image_urls))
        
        return image_urls
    
    def download_gallery(self, gallery_url):
        """Download all images from a Pixhost gallery"""
        print(f"\n📥 Scraping Pixhost gallery: {gallery_url}")
        print("-" * 60)
        
        try:
            # Extract gallery ID
            gallery_id = gallery_url.split('/gallery/')[-1].split('?')[0]
            print(f"Gallery ID: {gallery_id}\n")
            
            # Fetch gallery page
            print("🔍 Loading gallery page...")
            response = self.session.get(gallery_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Extract image URLs
            print("📋 Extracting image URLs...")
            image_urls = self.extract_image_urls_from_gallery(response.text, gallery_url)
            
            if not image_urls:
                print("✗ No images found in this gallery")
                return
            
            print(f"✓ Found {len(image_urls)} images\n")
            
            # Show samples
            print("Sample images:")
            for i, url in enumerate(image_urls[:5], 1):
                filename = os.path.basename(urlparse(url).path)
                print(f"  {i}. {filename[:50]}...")
            if len(image_urls) > 5:
                print(f"  ... and {len(image_urls) - 5} more")
            
            # Confirm download
            print(f"\n{'-'*60}")
            proceed = input(f"Download {len(image_urls)} images? (y/n): ").strip().lower()
            if proceed not in ['y', 'yes']:
                print("Download cancelled.")
                return
            
            # Create download folder
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            download_folder = os.path.join(self.download_path, f"pixhost_{gallery_id}_{timestamp}")
            os.makedirs(download_folder, exist_ok=True)
            
            # Download images
            print(f"\n{'='*60}")
            print("DOWNLOADING IMAGES")
            print('='*60)
            
            successful = 0
            failed = 0
            
            for i, img_url in enumerate(image_urls, 1):
                filename = os.path.basename(urlparse(img_url).path)
                
                # Remove query parameters
                if '?' in filename:
                    filename = filename.split('?')[0]
                
                if not filename or '.' not in filename:
                    filename = f"pixhost_{i:04d}.jpg"
                
                save_path = os.path.join(download_folder, filename)
                
                # Skip if exists
                if os.path.exists(save_path) and os.path.getsize(save_path) > 10240:
                    print(f"[{i}/{len(image_urls)}] ⊙ Exists: {filename[:45]}...")
                    successful += 1
                    continue
                
                try:
                    print(f"[{i}/{len(image_urls)}] Downloading: {filename[:45]}...", end=' ')
                    
                    # Download with retries
                    for attempt in range(3):
                        try:
                            img_response = self.session.get(img_url, headers=self.headers, 
                                                           stream=True, timeout=60)
                            img_response.raise_for_status()
                            break
                        except:
                            if attempt < 2:
                                time.sleep(2)
                                continue
                            else:
                                raise
                    
                    # Save file
                    with open(save_path, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    file_size = os.path.getsize(save_path)
                    
                    # Validate minimum size
                    if file_size < 10240:  # 10KB minimum
                        print(f"✗ Too small ({file_size/1024:.1f} KB)")
                        os.remove(save_path)
                        failed += 1
                    else:
                        size_kb = file_size / 1024
                        if size_kb > 1024:
                            print(f"✓ ({size_kb/1024:.2f} MB)")
                        else:
                            print(f"✓ ({size_kb:.1f} KB)")
                        successful += 1
                    
                except Exception as e:
                    print(f"✗ {type(e).__name__}")
                    failed += 1
                
                # Rate limiting
                time.sleep(0.5)
            
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print('='*60)
            print(f"Gallery ID: {gallery_id}")
            print(f"Successfully downloaded: {successful}/{len(image_urls)}")
            print(f"Failed: {failed}/{len(image_urls)}")
            print(f"Location: {download_folder}")
            
            if successful > 0:
                print(f"\n✓ Download complete!")
                try:
                    if sys.platform == 'win32':
                        os.startfile(download_folder)
                except:
                    pass
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def scrape(self, url):
        """Main entry point"""
        self.download_gallery(url)   

class KemonoScraper:
    """Scraper for kemono.party/kemono.cr/kemono.su using Playwright"""
    
    def __init__(self, output_dir: str = "downloads"):
        self.session = requests.Session()
        self.download_path = output_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        if self.browser:
            return
        
        print("🌐 Starting browser...")
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
    
    async def close_browser(self):
        """Close browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def get_rendered_page(self, url, max_retries=3):
        """Get fully rendered page content with retry logic"""
        if not self.browser:
            await self.init_browser()
        
        page = await self.context.new_page()
        
        for attempt in range(max_retries):
            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await page.wait_for_selector('article, .post, .card', timeout=20000)
                await asyncio.sleep(2)
                
                html_content = await page.content()
                await page.close()
                return html_content
                
            except Exception as e:
                error_type = type(e).__name__
                
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"  ✗ {error_type} (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                    
                    try:
                        await page.close()
                    except:
                        pass
                    
                    page = await self.context.new_page()
                    await asyncio.sleep(wait_time)
                else:
                    print(f"  ✗ {error_type} - all {max_retries} attempts failed")
                    try:
                        await page.close()
                    except:
                        pass
                    return None
        
        return None
    
    def extract_post_links_from_html(self, html_content, base_url):
        """Extract post links from rendered HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        post_links = []
        
        # Kemono uses /service/user/id/post/postid pattern
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/post/' in href:
                # Convert to absolute URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    parsed = urlparse(base_url)
                    full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                else:
                    full_url = urljoin(base_url, href)
                
                if full_url not in post_links:
                    post_links.append(full_url)
        
        return post_links
    
    def extract_pagination_info(self, html_content):
        """Extract pagination information from profile page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for pagination elements
        pagination_links = soup.find_all('a', href=True)
        max_offset = 0
        
        for link in pagination_links:
            href = link['href']
            # Kemono uses ?o=offset pattern
            if '?o=' in href:
                try:
                    offset = int(href.split('?o=')[-1].split('&')[0])
                    max_offset = max(max_offset, offset)
                except:
                    pass
        
        return max_offset
    
    async def get_all_post_links(self, profile_url):
        """Get ALL post links from profile by following pagination"""
        print("🔍 Loading profile page...")
        
        # Get first page
        html_content = await self.get_rendered_page(profile_url)
        
        if not html_content:
            print("✗ Could not load profile page")
            return []
        
        # Extract posts from first page
        all_post_links = self.extract_post_links_from_html(html_content, profile_url)
        print(f"✓ Extracted {len(all_post_links)} posts from page 1")
        
        # Detect pagination
        max_offset = self.extract_pagination_info(html_content)
        
        if max_offset > 0:
            # Kemono typically uses 50 posts per page
            pages_needed = (max_offset // 50) + 1
            print(f"📄 Need to scrape approximately {pages_needed} pages total")
            
            # Paginate through remaining pages
            current_offset = 50
            while current_offset <= max_offset:
                paginated_url = f"{profile_url}?o={current_offset}"
                
                page_num = (current_offset // 50) + 1
                print(f"  → Loading page {page_num} (offset {current_offset})...")
                
                page_html = await self.get_rendered_page(paginated_url)
                
                if page_html:
                    page_posts = self.extract_post_links_from_html(page_html, profile_url)
                    new_posts = [p for p in page_posts if p not in all_post_links]
                    all_post_links.extend(new_posts)
                    
                    print(f"    ✓ Found {len(new_posts)} new posts (total: {len(all_post_links)})")
                    
                    if len(new_posts) == 0:
                        print(f"    ℹ No more new posts, stopping pagination")
                        break
                else:
                    print(f"    ✗ Failed to load page after all retries")
                
                current_offset += 50
                await asyncio.sleep(2)
        
        return all_post_links
    
    def extract_media_from_html(self, html_content, base_url):
        """Extract media URLs from rendered post HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        media_urls = set()
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # Pattern 1: Links with /data/ or /files/
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/data/' in href or '/files/' in href:
                if href.startswith('http'):
                    media_urls.add(href)
                elif href.startswith('/'):
                    media_urls.add(f"{base_domain}{href}")
        
        # Pattern 2: Image tags
        for img in soup.find_all('img', src=True):
            src = img['src']
            if '/data/' in src or '/files/' in src or '/thumbnail/' in src:
                if '/thumbnail/' in src:
                    src = src.replace('/thumbnail/', '/data/')
                
                if src.startswith('http'):
                    media_urls.add(src)
                elif src.startswith('/'):
                    media_urls.add(f"{base_domain}{src}")
        
        # Pattern 3: Video/source tags
        for video in soup.find_all(['video', 'source'], src=True):
            src = video['src']
            if src.startswith('http'):
                media_urls.add(src)
            elif src.startswith('/'):
                media_urls.add(f"{base_domain}{src}")
        
        # Pattern 4: Look for kemono data/files URLs in HTML
        data_pattern = r'(https?://(?:kemono\.party|kemono\.cr|kemono\.su)/(?:data|files)/[^\s\'"<>]+)'
        matches = re.findall(data_pattern, html_content, re.IGNORECASE)
        media_urls.update(matches)
        
        return list(media_urls)
    
    async def download_single_post(self, post_url, user_folder):
        """Download all media from a single post"""
        if not self.browser:
            await self.init_browser()
        
        page = await self.context.new_page()
        failed_urls = []
        
        try:
            await page.goto(post_url, wait_until='networkidle', timeout=30000)
            
            try:
                await page.wait_for_selector('img[src*="/data/"], a[href*="/data/"], video', timeout=10000)
            except:
                await asyncio.sleep(3)
            
            html_content = await page.content()
            await page.close()
            
            media_urls = self.extract_media_from_html(html_content, post_url)
            
            if not media_urls:
                return 0, 0, []
            
            # Deduplicate
            seen_hashes = set()
            unique_urls = []
            
            for url in media_urls:
                hash_match = re.search(r'/([a-f0-9]{32,})', url, re.IGNORECASE)
                if hash_match:
                    file_hash = hash_match.group(1)
                    if file_hash not in seen_hashes:
                        seen_hashes.add(file_hash)
                        unique_urls.append(url)
                else:
                    unique_urls.append(url)
            
            media_urls = unique_urls
            
            if not media_urls:
                return 0, 0, []
            
            video_count = len([u for u in media_urls if any(ext in u.lower() for ext in ['.mp4', '.webm'])])
            image_count = len(media_urls) - video_count
            
            print(f"  ✓ Found {len(media_urls)} unique files ({image_count} images, {video_count} videos)")
            
            successful = 0
            failed = 0
            
            for i, media_url in enumerate(media_urls, 1):
                is_video = any(ext in media_url.lower() for ext in ['.mp4', '.webm'])
                file_type = "VIDEO" if is_video else "IMAGE"
                
                filename = os.path.basename(urlparse(media_url).path)
                if not filename or len(filename) < 5:
                    ext = '.mp4' if is_video else '.jpg'
                    filename = f"file_{i:03d}{ext}"
                
                save_path = os.path.join(user_folder, filename)
                
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    print(f"    [{i}/{len(media_urls)}] [{file_type}] ⊙ Exists: {filename[:35]}...")
                    successful += 1
                    continue
                
                max_retries = 5
                retry_delay = 3
                
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            print(f"    [{i}/{len(media_urls)}] [{file_type}] Retry {attempt}/{max_retries-1}: {filename[:35]}...", end=' ')
                        else:
                            print(f"    [{i}/{len(media_urls)}] [{file_type}] Downloading: {filename[:35]}...", end=' ')
                        
                        timeout_duration = 180 if is_video else 90
                        
                        # Set referer to kemono domain
                        download_headers = self.headers.copy()
                        download_headers['Referer'] = urlparse(media_url).scheme + '://' + urlparse(media_url).netloc + '/'
                        
                        response = self.session.get(
                            media_url,
                            headers=download_headers,
                            stream=True,
                            timeout=timeout_duration
                        )
                        
                        if response.status_code in [500, 503]:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)
                                print(f"✗ HTTP {response.status_code} (waiting {wait_time}s...)")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                print(f"✗ HTTP {response.status_code} (exhausted retries)")
                                failed += 1
                                failed_urls.append((media_url, filename, f"HTTP {response.status_code}"))
                                break
                        
                        response.raise_for_status()
                        
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        actual_size = os.path.getsize(save_path)
                        min_size = 1024 if is_video else 51200
                        
                        if actual_size < min_size:
                            size_kb = actual_size / 1024
                            print(f"✗ Too small ({size_kb:.1f} KB)")
                            os.remove(save_path)
                            failed += 1
                            failed_urls.append((media_url, filename, f"Too small: {size_kb:.1f} KB"))
                        else:
                            size_kb = actual_size / 1024
                            if size_kb > 1024:
                                print(f"✓ ({size_kb/1024:.2f} MB)")
                            else:
                                print(f"✓ ({size_kb:.1f} KB)")
                            successful += 1
                        
                        break
                        
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"✗ Timeout (waiting {wait_time}s...)")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"✗ Timeout (exhausted retries)")
                            failed += 1
                            failed_urls.append((media_url, filename, "Timeout"))
                            
                    except Exception as e:
                        error_name = type(e).__name__
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"✗ {error_name} (waiting {wait_time}s...)")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"✗ {error_name} (exhausted retries)")
                            failed += 1
                            failed_urls.append((media_url, filename, error_name))
                
                import random
                base_delay = 1.5 if not is_video else 2.5
                jitter = random.uniform(0, 0.5)
                await asyncio.sleep(base_delay + jitter)
            
            return successful, failed, failed_urls
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            try:
                await page.close()
            except:
                pass
            return 0, 1, []
    
    async def download_user_profile_async(self, url):
        """Download all posts from user profile (async version)"""
        print(f"\n📥 Scraping Kemono user profile: {url}")
        print("-" * 60)
        
        try:
            # Extract service and user ID
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            service = path_parts[0] if len(path_parts) > 0 else 'unknown'
            user_id = path_parts[2] if len(path_parts) > 2 else 'unknown'
            
            print(f"Service: {service}")
            print(f"User ID: {user_id}")
            print()
            
            # Get ALL post links with pagination
            post_links = await self.get_all_post_links(url)
            
            if not post_links:
                print("✗ No posts found on this profile")
                return
            
            print(f"\n✓ Total posts found: {len(post_links)}")
            
            # Show sample
            print("\nSample posts:")
            for i, link in enumerate(post_links[:10], 1):
                post_id = link.split('/post/')[-1].split('?')[0] if '/post/' in link else 'unknown'
                print(f"  {i}. Post {post_id}")
            if len(post_links) > 10:
                print(f"  ... and {len(post_links) - 10} more")
            
            # Ask user
            print(f"\n{'='*60}")
            print("DOWNLOAD OPTIONS")
            print('='*60)
            print(f"1. Download ALL {len(post_links)} posts")
            print(f"2. Download first N posts")
            print(f"3. Download specific range (e.g., 1-100)")
            print(f"4. Cancel")
            
            choice = input("\nChoose option (1/2/3/4): ").strip()
            
            if choice == '4':
                print("Download cancelled.")
                return
            elif choice == '2':
                try:
                    n = int(input(f"How many posts? (1-{len(post_links)}): ").strip())
                    post_links = post_links[:n]
                    print(f"✓ Will download first {len(post_links)} posts")
                except:
                    print("Invalid, downloading all.")
            elif choice == '3':
                try:
                    range_input = input("Enter range (e.g., 1-100 or 50-150): ").strip()
                    if '-' in range_input:
                        start, end = map(int, range_input.split('-'))
                        start = max(1, start) - 1
                        end = min(len(post_links), end)
                        post_links = post_links[start:end]
                        print(f"✓ Will download posts {start+1} to {end}")
                except:
                    print("Invalid range, downloading all.")
            
            # Create folder
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            user_folder = os.path.join(self.download_path, f"kemono_{service}_{user_id}_{timestamp}")
            os.makedirs(user_folder, exist_ok=True)
            
            # Download each post
            print(f"\n{'='*60}")
            print("DOWNLOADING POSTS")
            print('='*60)
            
            total_files = 0
            total_failed = 0
            all_failed_urls = []
            
            for i, post_url in enumerate(post_links, 1):
                post_id = post_url.split('/post/')[-1].split('?')[0] if '/post/' in post_url else f'{i}'
                print(f"\n[{i}/{len(post_links)}] Post {post_id}:")
                
                successful, failed, failed_urls = await self.download_single_post(post_url, user_folder)
                total_files += successful
                total_failed += failed
                
                if failed_urls:
                    for url, filename, error in failed_urls:
                        all_failed_urls.append((post_id, url, filename, error))
                
                await asyncio.sleep(1)
            
            # Summary
            print(f"\n{'='*60}")
            print("DOWNLOAD SUMMARY")
            print('='*60)
            print(f"User ID: {user_id}")
            print(f"Service: {service}")
            print(f"Total posts processed: {len(post_links)}")
            print(f"Total files downloaded: {total_files}")
            print(f"Total files failed: {total_failed}")
            print(f"Location: {user_folder}")
            
            # Save failed URLs to file
            if all_failed_urls:
                failed_log = os.path.join(user_folder, "failed_downloads.txt")
                with open(failed_log, 'w', encoding='utf-8') as f:
                    f.write(f"Failed Downloads from User {user_id} ({service})\n")
                    f.write(f"Downloaded: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total failed: {len(all_failed_urls)}\n")
                    f.write("="*80 + "\n\n")
                    
                    for post_id, url, filename, error in all_failed_urls:
                        f.write(f"Post: {post_id}\n")
                        f.write(f"Filename: {filename}\n")
                        f.write(f"Error: {error}\n")
                        f.write(f"URL: {url}\n")
                        f.write("-"*80 + "\n")
                
                print(f"\n⚠ {total_failed} files failed - saved to: failed_downloads.txt")
            
            if total_files > 0:
                print(f"\n✓ Download successful!")
                try:
                    if sys.platform == 'win32':
                        os.startfile(user_folder)
                except:
                    pass
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()
    
    async def scrape(self, url):
        """Main entry point (async)"""
        await self.download_user_profile_async(url)        


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Scraper (Bunkr + Pixeldrain + Simpcity + Galleries + Coomer + Fapello + Pixhost + Kemono)')
    parser.add_argument('url', nargs='?', help='Profile/album/thread URL')
    parser.add_argument('-o', '--output', default='downloads', help='Output directory')
    parser.add_argument('--mode', choices=['auto', 'bunkr', 'pixeldrain', 'forum', 'gallery', 'coomer', 'fapello', 'pixhost', 'kemono'], default='auto')  # ← ADDED 'kemono'
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--key', help='Pixeldrain API key (optional)')
    
    args = parser.parse_args()
    
    # Interactive mode if no URL provided
    if not args.url:
        print("Choose scraper mode:")
        print("1. Bunkr album/file")
        print("2. Pixeldrain album/file")
        print("3. Simpcity forum thread")
        print("4. Generic gallery (viralthots.tv, etc.)")
        print("5. Coomer.st (user profiles)")
        print("6. Fapello.com (user profiles)")
        print("7. Pixhost.to (galleries)")
        print("8. Kemono Party (user profiles)")  # ← FIXED: Now 8
        print("9. Auto-detect from URL")  # ← FIXED: Now 9
        
        mode_choice = input("\nChoose option (1-9): ").strip()
        
        url = input("Enter URL: ").strip()
        
        mode_map = {
            '1': 'bunkr',
            '2': 'pixeldrain',
            '3': 'forum',
            '4': 'gallery',
            '5': 'coomer',
            '6': 'fapello',
            '7': 'pixhost',
            '8': 'kemono',  # ← ADDED
        }
        
        args.mode = mode_map.get(mode_choice, 'auto')
        args.url = url
    
    # Auto-detect mode if not specified
    if args.mode == 'auto':
        url_lower = args.url.lower()
        if 'kemono' in url_lower:
            args.mode = 'kemono'
        elif 'pixhost' in url_lower:
            args.mode = 'pixhost'
        elif 'fapello' in url_lower:
            args.mode = 'fapello'
        elif 'coomer' in url_lower:
            args.mode = 'coomer'
        elif 'simpcity' in url_lower or '/threads/' in url_lower:
            args.mode = 'forum'
        elif 'pixeldrain' in url_lower:
            args.mode = 'pixeldrain'
        elif 'bunkr' in url_lower:
            args.mode = 'bunkr'
        else:
            args.mode = 'gallery'
    
    # Run appropriate scraper
    if args.mode == 'kemono':
        print("🔧 Mode: Kemono Party Scraper\n")
        scraper = KemonoScraper(output_dir=args.output)
        await scraper.scrape(args.url)    
    elif args.mode == 'pixhost':
        print("🔧 Mode: Pixhost Gallery Scraper\n")
        scraper = PixhostScraper(output_dir=args.output)
        scraper.download_gallery(args.url)
    elif args.mode == 'fapello':
        print("🔧 Mode: Fapello Scraper\n")
        scraper = FapelloScraper(output_dir=args.output)
        await scraper.scrape(args.url)
    elif args.mode == 'forum':
        print("🔧 Mode: Simpcity Forum Scraper\n")
        downloader = ForumImageDownloader(output_dir=args.output, debug_mode=args.debug)
        downloader.download_images(args.url)
    elif args.mode == 'coomer':
        print("🔧 Mode: Coomer.st Scraper\n")
        scraper = CoomerScraper(output_dir=args.output)
        await scraper.scrape(args.url)
    elif args.mode == 'gallery':
        print("🔧 Mode: Generic Gallery Scraper\n")
        downloader = GenericGalleryDownloader(output_dir=args.output)
        downloader.download_images(args.url)
    else:
        print(f"🔧 Mode: Bunkr/Pixeldrain Scraper\n")
        scraper = UniversalScraper(
            output_dir=args.output,
            pixeldrain_api_key=args.key
        )
        await scraper.scrape(args.url)
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
