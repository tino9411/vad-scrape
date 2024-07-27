from .base_scraper import BaseScraper
from urllib.parse import quote, urljoin
import os
import logging
from colorama import Fore, Style
import time
from file_downloader import download_file, terminate
import aiohttp
import asyncio

class TVShowScraper(BaseScraper):
    def extract_links(self, soup):
        elements = soup.find_all('div', class_='centerflex name-div')
        links = []

        for element in elements:
            link = element.find('a', href=True)
            if link:
                href = urljoin(self.base_url, link['href'])
                name = link.get_text(separator=' ', strip=True)
                if name.lower() != "parent directory":
                    links.append({'name': name, 'url': href})

        return links

    def extract_file_links(self, soup):
        elements = soup.find_all('a', class_='file-entry wrap')
        links = []

        for element in elements:
            href = urljoin(self.base_url, element['href'])
            name = element.get_text(separator=' ', strip=True)
            links.append({'name': name, 'url': href})

        return links

    async def get_file_size(self, session, url):
        try:
            async with session.head(url) as response:
                if response.status == 200:
                    return int(response.headers.get('Content-Length', 0))
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching file size: {e}")
        return 0

    async def download_episode(self, session, show_name, season, episode, season_path, i, total_episodes):
        episode_name = self.sanitize_filename(episode['name'])
        episode_url = episode['url']
        episode_path = os.path.join(season_path, episode_name)
        
        expected_size = await self.get_file_size(session, episode_url)
        
        if os.path.exists(episode_path):
            local_size = os.path.getsize(episode_path)
            if expected_size == 0 or local_size == expected_size:
                print(f"{Fore.CYAN}Skipping completed episode: {episode_name}{Style.RESET_ALL}")
                return None
            elif local_size < expected_size:
                print(f"{Fore.YELLOW}Resuming incomplete download: {Fore.CYAN}{episode_name}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Progress: {Fore.CYAN}{local_size/expected_size*100:.2f}% completed{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Local file larger than expected. Re-downloading: {Fore.CYAN}{episode_name}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}Starting new download: {Fore.CYAN}{episode_name}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Progress: {Fore.CYAN}{i}/{total_episodes} episodes{Style.RESET_ALL}")
        try:
            start_time = time.time()
            result = await download_file(session, episode_url, episode_path, expected_size)
            end_time = time.time()
            if result:
                download_time = end_time - start_time
                size_mb = os.path.getsize(episode_path) / (1024 * 1024)
                speed_mbps = size_mb / download_time if download_time > 0 else 0
                logging.info(f"{Fore.GREEN}Successfully downloaded: {Fore.CYAN}{episode_name}{Style.RESET_ALL}")
                logging.info(f"{Fore.GREEN}Download time: {Fore.CYAN}{download_time:.2f} seconds{Style.RESET_ALL}")
                logging.info(f"{Fore.GREEN}Average speed: {Fore.CYAN}{speed_mbps:.2f} MB/s{Style.RESET_ALL}")
                return {
                    "episode_name": episode_name,
                    "download_time": download_time,
                    "size_mb": size_mb,
                    "speed_mbps": speed_mbps
                }
            else:
                logging.error(f"{Fore.RED}Failed to download episode: {Fore.CYAN}{episode_name}{Style.RESET_ALL}")
                return None
        except Exception as e:
            logging.error(f"Failed to download episode: {episode_name}. Error: {e}")
            logging.error(f"Error details: {str(e)}")
            print(f"{Fore.RED}Failed to download episode: {Fore.CYAN}{episode_name}{Fore.RED}. Error: {e}{Style.RESET_ALL}")
            return None

    async def download_item(self, session, show_name, season, episodes, season_path, concurrency=1):
        history = self.load_history()
        show_history = history.setdefault(show_name, {})
        season_history = show_history.setdefault(season['name'], {"episodes": {}, "last_download": ""})
        
        total_episodes = len(episodes)
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def download_with_semaphore(episode, i):
            async with semaphore:
                return await self.download_episode(session, show_name, season, episode, season_path, i, total_episodes)
        
        tasks = [asyncio.create_task(download_with_semaphore(episode, i)) 
                 for i, episode in enumerate(episodes, 1)]
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                season_history["episodes"][result["episode_name"]] = {
                    "download_time": result["download_time"],
                    "size_mb": result["size_mb"],
                    "speed_mbps": result["speed_mbps"]
                }
        
        season_history["last_download"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save_history(history)
        
        print(f"\n{Fore.GREEN}Download process completed for {show_name} - {season['name']}.{Style.RESET_ALL}")

    async def search_and_download(self, search_query, concurrency=1):
        search_url = f"{self.base_url}/s/{quote(search_query)}"
        
        async with aiohttp.ClientSession() as session:
            soup = await self.fetch_page_with_verification(session, search_url)
            if not soup:
                logging.error(f"Failed to fetch search results page: {search_url}")
                return

            shows = self.extract_links(soup)
            if not shows:
                print(f"{Fore.RED}No TV shows found for the search query: {search_query}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.YELLOW}Found the following TV shows:{Style.RESET_ALL}")
            for i, show in enumerate(shows, 1):
                print(f"{Fore.GREEN}{i}. {Fore.CYAN}{show['name']} {Fore.MAGENTA}- {show['url']}{Style.RESET_ALL}")

            while True:
                choice = input(f"\n{Fore.YELLOW}Enter the number of the TV show you want to download (or 'q' to quit): {Style.RESET_ALL}").strip().lower()
                if choice == 'q':
                    return
                if choice.isdigit() and 1 <= int(choice) <= len(shows):
                    selected_show = shows[int(choice) - 1]
                    break
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

            show_soup = await self.fetch_page_with_verification(session, selected_show['url'])
            if not show_soup:
                logging.error(f"Failed to fetch TV show page: {selected_show['url']}")
                return

            seasons = self.extract_links(show_soup)
            if not seasons:
                print(f"{Fore.RED}No seasons found for {selected_show['name']}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.YELLOW}Found seasons for TV show {Fore.CYAN}{selected_show['name']}{Fore.YELLOW}:{Style.RESET_ALL}")
            for i, season in enumerate(seasons, 1):
                print(f"{Fore.GREEN}{i}. {Fore.CYAN}{season['name']} {Fore.MAGENTA}- {season['url']}{Style.RESET_ALL}")

            season_choice = input(f"\n{Fore.YELLOW}Enter the number of the season to download (or 'all' for all seasons): {Style.RESET_ALL}").strip().lower()
            
            if season_choice == 'all':
                selected_seasons = seasons
            elif season_choice.isdigit() and 1 <= int(season_choice) <= len(seasons):
                selected_seasons = [seasons[int(season_choice) - 1]]
            else:
                print(f"{Fore.RED}Invalid choice. Exiting.{Style.RESET_ALL}")
                return

            for season in selected_seasons:
                if terminate:
                    break
                
                season_soup = await self.fetch_page_with_verification(session, season['url'])
                if not season_soup:
                    logging.error(f"Failed to fetch season page: {season['url']}")
                    continue

                episodes = self.extract_file_links(season_soup)
                if not episodes:
                    print(f"{Fore.RED}No episodes found for {season['name']}{Style.RESET_ALL}")
                    continue

                show_name = self.sanitize_filename(selected_show['name'])
                season_name = self.sanitize_filename(season['name'])
                season_path = os.path.join(self.download_dir, show_name, season_name)
                try:
                    os.makedirs(season_path, exist_ok=True)
                    logging.info(f"Created directory: {Fore.CYAN}{season_path}{Style.RESET_ALL}")
                except Exception as e:
                    logging.error(f"Failed to create directory: {season_path}. Error: {e}")
                    continue

                await self.download_item(session, show_name, season, episodes, season_path, concurrency)

        print(f"{Fore.GREEN}Download process completed.{Style.RESET_ALL}")