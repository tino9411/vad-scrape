from .base_scraper import BaseScraper
from urllib.parse import quote, urljoin
import os
import logging
from colorama import Fore, Style
import time
from file_downloader import download_file, terminate
import aiohttp
import asyncio

class MovieScraper(BaseScraper):
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

    async def download_file(self, session, movie_name, movie_file, movie_path, i, total_files):
        file_name = self.sanitize_filename(movie_file['name'])
        file_url = movie_file['url']
        file_path = os.path.join(movie_path, file_name)
        
        expected_size = await self.get_file_size(session, file_url)
        
        if os.path.exists(file_path):
            local_size = os.path.getsize(file_path)
            if expected_size == 0 or local_size == expected_size:
                print(f"{Fore.CYAN}Skipping completed file: {file_name}{Style.RESET_ALL}")
                return None
            elif local_size < expected_size:
                print(f"{Fore.YELLOW}Resuming incomplete download: {Fore.CYAN}{file_name}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Progress: {Fore.CYAN}{local_size/expected_size*100:.2f}% completed{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Local file larger than expected. Re-downloading: {Fore.CYAN}{file_name}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}Starting new download: {Fore.CYAN}{file_name}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}Progress: {Fore.CYAN}{i}/{total_files} files{Style.RESET_ALL}")
        try:
            start_time = time.time()
            result = await download_file(session, file_url, file_path, expected_size)
            end_time = time.time()
            if result:
                download_time = end_time - start_time
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                speed_mbps = size_mb / download_time if download_time > 0 else 0
                logging.info(f"{Fore.GREEN}Successfully downloaded: {Fore.CYAN}{file_name}{Style.RESET_ALL}")
                logging.info(f"{Fore.GREEN}Download time: {Fore.CYAN}{download_time:.2f} seconds{Style.RESET_ALL}")
                logging.info(f"{Fore.GREEN}Average speed: {Fore.CYAN}{speed_mbps:.2f} MB/s{Style.RESET_ALL}")
                return {
                    "file_name": file_name,
                    "download_time": download_time,
                    "size_mb": size_mb,
                    "speed_mbps": speed_mbps
                }
            else:
                logging.error(f"{Fore.RED}Failed to download file: {Fore.CYAN}{file_name}{Style.RESET_ALL}")
                return None
        except Exception as e:
            logging.error(f"Failed to download file: {file_name}. Error: {e}")
            logging.error(f"Error details: {str(e)}")
            print(f"{Fore.RED}Failed to download file: {Fore.CYAN}{file_name}{Fore.RED}. Error: {e}{Style.RESET_ALL}")
            return None

    async def download_item(self, session, movie_name, movie_files, movie_path, concurrency=1):
        history = self.load_history()
        movie_history = history.setdefault(movie_name, {"files": {}, "last_download": ""})
        
        total_files = len(movie_files)
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def download_with_semaphore(movie_file, i):
            async with semaphore:
                return await self.download_file(session, movie_name, movie_file, movie_path, i, total_files)
        
        tasks = [asyncio.create_task(download_with_semaphore(movie_file, i)) 
                 for i, movie_file in enumerate(movie_files, 1)]
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                movie_history["files"][result["file_name"]] = {
                    "download_time": result["download_time"],
                    "size_mb": result["size_mb"],
                    "speed_mbps": result["speed_mbps"]
                }
        
        movie_history["last_download"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save_history(history)
        
        print(f"\n{Fore.GREEN}Download process completed for {movie_name}.{Style.RESET_ALL}")

    async def search_and_download(self, search_query, concurrency=1):
        search_url = f"{self.base_url}/s/{quote(search_query)}"
        
        async with aiohttp.ClientSession() as session:
            soup = await self.fetch_page(session, search_url)
            if not soup:
                logging.error(f"Failed to fetch search results page: {search_url}")
                return

            movies = self.extract_links(soup)
            if not movies:
                print(f"{Fore.RED}No movies found for the search query: {search_query}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.YELLOW}Found the following movies:{Style.RESET_ALL}")
            for i, movie in enumerate(movies, 1):
                print(f"{Fore.GREEN}{i}. {Fore.CYAN}{movie['name']} {Fore.MAGENTA}- {movie['url']}{Style.RESET_ALL}")

            while True:
                choice = input(f"\n{Fore.YELLOW}Enter the number of the movie you want to download (or 'q' to quit): {Style.RESET_ALL}").strip().lower()
                if choice == 'q':
                    return
                if choice.isdigit() and 1 <= int(choice) <= len(movies):
                    selected_movie = movies[int(choice) - 1]
                    break
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

            movie_soup = await self.fetch_page(session, selected_movie['url'])
            if not movie_soup:
                logging.error(f"Failed to fetch movie page: {selected_movie['url']}")
                return

            movie_files = self.extract_file_links(movie_soup)
            if not movie_files:
                print(f"{Fore.RED}No files found for {selected_movie['name']}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.YELLOW}Available files for {selected_movie['name']}:{Style.RESET_ALL}")
            for i, file in enumerate(movie_files, 1):
                print(f"{Fore.GREEN}{i}. {Fore.CYAN}{file['name']}{Style.RESET_ALL}")

            while True:
                file_choice = input(f"\n{Fore.YELLOW}Enter the numbers of the files you want to download (comma-separated), 'all' for all files, or 'q' to quit: {Style.RESET_ALL}").strip().lower()
                if file_choice == 'q':
                    return
                if file_choice == 'all':
                    selected_files = movie_files
                    break
                try:
                    choices = [int(c.strip()) for c in file_choice.split(',')]
                    selected_files = [movie_files[i-1] for i in choices if 1 <= i <= len(movie_files)]
                    if selected_files:
                        break
                    else:
                        print(f"{Fore.RED}No valid files selected. Please try again.{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Invalid input. Please enter comma-separated numbers, 'all', or 'q'.{Style.RESET_ALL}")

            movie_name = self.sanitize_filename(selected_movie['name'])
            movie_path = os.path.join(self.download_dir, movie_name)
            try:
                os.makedirs(movie_path, exist_ok=True)
                logging.info(f"Created directory: {Fore.CYAN}{movie_path}{Style.RESET_ALL}")
            except Exception as e:
                logging.error(f"Failed to create directory: {movie_path}. Error: {e}")
                return

            await self.download_item(session, movie_name, selected_files, movie_path, concurrency)

        print(f"{Fore.GREEN}Download process completed.{Style.RESET_ALL}")