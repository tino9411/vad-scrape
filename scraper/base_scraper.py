import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import os
import re
import logging
import json
import time
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BaseScraper:
    def __init__(self, base_url, download_dir, headers=None, max_workers=5):
        self.base_url = base_url
        self.download_dir = download_dir
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.max_workers = max_workers
        self.history_file = os.path.join(self.download_dir, 'download_history.json')
        self.init_history_file()
        self.driver = None

    def init_history_file(self):
        if not os.path.exists(self.history_file):
            self.save_history({})

    async def fetch_page(self, session, url, retries=3):
        for attempt in range(retries):
            try:
                logging.info(f"Fetching URL: {url}")
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    logging.info(f"Status Code: {response.status}")
                    return BeautifulSoup(await response.text(), 'html.parser')
            except aiohttp.ClientError as e:
                logging.error(f"Error fetching URL: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None

    def sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON in history file: {self.history_file}")
                logging.info("Creating a new history file.")
                return {}
            except Exception as e:
                logging.error(f"Error reading history file: {self.history_file}. Error: {str(e)}")
                logging.info("Creating a new history file.")
                return {}
        return {}

    def save_history(self, history):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving history to file: {self.history_file}. Error: {str(e)}")

    def display_download_history(self):
        history = self.load_history()
        if not history:
            print(f"{Fore.YELLOW}No download history available.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.GREEN}Download History:{Style.RESET_ALL}")
        for item_name, item_data in history.items():
            print(f"\n{Fore.CYAN}Item: {item_name}{Style.RESET_ALL}")
            if isinstance(item_data, dict) and 'last_download' in item_data:
                print(f"  Last download: {item_data['last_download']}")
                if 'files' in item_data:
                    print(f"  Files:")
                    for file_name, file_data in item_data['files'].items():
                        print(f"    - {file_name}")
                        print(f"      Size: {file_data['size_mb']:.2f} MB")
                        print(f"      Download time: {file_data['download_time']:.2f} seconds")
                        print(f"      Speed: {file_data['speed_mbps']:.2f} MB/s")
            elif isinstance(item_data, dict):
                for season_name, season_data in item_data.items():
                    print(f"  Season: {season_name}")
                    print(f"    Last download: {season_data.get('last_download', 'N/A')}")
                    if 'episodes' in season_data:
                        print(f"    Episodes:")
                        for episode_name, episode_data in season_data['episodes'].items():
                            print(f"      - {episode_name}")
                            print(f"        Size: {episode_data['size_mb']:.2f} MB")
                            print(f"        Download time: {episode_data['download_time']:.2f} seconds")
                            print(f"        Speed: {episode_data['speed_mbps']:.2f} MB/s")

    def handle_human_verification(self, url):
        if not self.driver:
            self.driver = webdriver.Chrome()  # or another driver like webdriver.Firefox()
        
        self.driver.get(url)
        print(f"{Fore.YELLOW}Please complete the human verification in the browser window and press Enter here to continue...{Style.RESET_ALL}")
        input()
        page_source = self.driver.page_source
        return BeautifulSoup(page_source, 'html.parser')

    # To be implemented by subclasses
    def extract_links(self, soup):
        raise NotImplementedError

    # To be implemented by subclasses
    def extract_file_links(self, soup):
        raise NotImplementedError

    # To be implemented by subclasses
    async def download_item(self, session, item_name, item_files, item_path):
        raise NotImplementedError

    # To be implemented by subclasses
    async def search_and_download(self, search_query):
        raise NotImplementedError

    async def fetch_page_with_verification(self, session, url, retries=3):
        soup = await self.fetch_page(session, url, retries)
        if soup and "human verification" in str(soup).lower():  # Adjust condition to detect when verification is needed
            soup = self.handle_human_verification(url)
        return soup