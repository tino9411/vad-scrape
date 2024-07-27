from .base_scraper import BaseScraper
from urllib.parse import quote, urljoin
import os
import logging
from colorama import Fore, Style
import time
from file_downloader import download_file, terminate
import aiohttp
import asyncio

class AnimeScraper(BaseScraper):
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

    async def navigate_folders(self, session, url, path_so_far=[]):
        soup = await self.fetch_page_with_verification(session, url)
        if not soup:
            logging.error(f"Failed to fetch page: {url}")
            return None

        links = self.extract_links(soup)
        files = self.extract_file_links(soup)

        if files:
            return {'type': 'files', 'url': url, 'files': files, 'path': path_so_far}

        print(f"\n{Fore.YELLOW}Current folder: {' > '.join(path_so_far)}{Style.RESET_ALL}")
        for i, link in enumerate(links, 1):
            print(f"{Fore.GREEN}{i}. {Fore.CYAN}{link['name']}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{len(links) + 1}. {Fore.CYAN}[Download this folder]{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{len(links) + 2}. {Fore.CYAN}[Go back]{Style.RESET_ALL}")

        while True:
            choice = input(f"\n{Fore.YELLOW}Enter your choice (1-{len(links) + 2}): {Style.RESET_ALL}").strip()
            if choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= len(links):
                    new_path = path_so_far + [links[choice - 1]['name']]
                    return await self.navigate_folders(session, links[choice - 1]['url'], new_path)
                elif choice == len(links) + 1:
                    return {'type': 'folder', 'url': url, 'path': path_so_far}
                elif choice == len(links) + 2:
                    return {'type': 'back'}
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

    async def download_folder(self, session, url, folder_path, concurrency):
        soup = await self.fetch_page_with_verification(session, url)
        if not soup:
            logging.error(f"Failed to fetch folder page: {url}")
            return

        files = self.extract_file_links(soup)
        links = self.extract_links(soup)

        # Download subfolders recursively
        subfolder_tasks = [
            self.download_folder(session, link['url'], os.path.join(folder_path, self.sanitize_filename(link['name'])), concurrency)
            for link in links
        ]
        await asyncio.gather(*subfolder_tasks)

        # Download files in the current folder
        if files:
            os.makedirs(folder_path, exist_ok=True)
            semaphore = asyncio.Semaphore(concurrency)
            download_tasks = [
                self.download_file_with_semaphore(session, file['url'], os.path.join(folder_path, self.sanitize_filename(file['name'])), semaphore)
                for file in files
            ]
            await asyncio.gather(*download_tasks)

    async def download_file_with_semaphore(self, session, url, path, semaphore):
        async with semaphore:
            await self.download_file(session, url, path)

    async def download_file(self, session, url, path):
        expected_size = await self.get_file_size(session, url)
        result = await download_file(session, url, path, expected_size)
        if result:
            downloaded_path, download_time, speed_mbps = result
            print(f"{Fore.GREEN}Successfully downloaded: {os.path.basename(path)}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Download time: {download_time:.2f} seconds{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Average speed: {speed_mbps:.2f} MB/s{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to download: {os.path.basename(path)}{Style.RESET_ALL}")

    async def get_file_size(self, session, url):
        try:
            async with session.head(url) as response:
                if response.status == 200:
                    return int(response.headers.get('Content-Length', 0))
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching file size: {e}")
        return 0

    async def search_and_download(self, search_query, concurrency=1):
        search_url = f"{self.base_url}/s/{quote(search_query)}"
        
        async with aiohttp.ClientSession() as session:
            soup = await self.fetch_page_with_verification(session, search_url)
            if not soup:
                logging.error(f"Failed to fetch search results page: {search_url}")
                return

            anime_list = self.extract_links(soup)
            if not anime_list:
                print(f"{Fore.RED}No anime found for the search query: {search_query}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.YELLOW}Found the following anime:{Style.RESET_ALL}")
            for i, anime in enumerate(anime_list, 1):
                print(f"{Fore.GREEN}{i}. {Fore.CYAN}{anime['name']} {Fore.MAGENTA}- {anime['url']}{Style.RESET_ALL}")

            while True:
                choice = input(f"\n{Fore.YELLOW}Enter the number of the anime you want to explore (or 'q' to quit): {Style.RESET_ALL}").strip().lower()
                if choice == 'q':
                    return
                if choice.isdigit() and 1 <= int(choice) <= len(anime_list):
                    selected_anime = anime_list[int(choice) - 1]
                    break
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

            while True:
                result = await self.navigate_folders(session, selected_anime['url'], [selected_anime['name']])
                if result is None or result['type'] == 'back':
                    break
                
                if result['type'] == 'files':
                    print(f"\n{Fore.YELLOW}Available files:{Style.RESET_ALL}")
                    for i, file in enumerate(result['files'], 1):
                        print(f"{Fore.GREEN}{i}. {Fore.CYAN}{file['name']}{Style.RESET_ALL}")
                    
                    file_choice = input(f"\n{Fore.YELLOW}Enter the numbers of the files you want to download (comma-separated), 'all' for all files, or 'b' to go back: {Style.RESET_ALL}").strip().lower()
                    if file_choice == 'b':
                        continue
                    if file_choice == 'all':
                        selected_files = result['files']
                    else:
                        try:
                            choices = [int(c.strip()) for c in file_choice.split(',')]
                            selected_files = [result['files'][i-1] for i in choices if 1 <= i <= len(result['files'])]
                        except ValueError:
                            print(f"{Fore.RED}Invalid input. Please enter comma-separated numbers or 'all'.{Style.RESET_ALL}")
                            continue

                    folder_path = os.path.join(self.download_dir, *result['path'])
                    os.makedirs(folder_path, exist_ok=True)
                    semaphore = asyncio.Semaphore(concurrency)
                    download_tasks = []
                    for file in selected_files:
                        file_path = os.path.join(folder_path, self.sanitize_filename(file['name']))
                        task = asyncio.create_task(self.download_file_with_semaphore(session, file['url'], file_path, semaphore))
                        download_tasks.append(task)
                    await asyncio.gather(*download_tasks)
                    break

                elif result['type'] == 'folder':
                    folder_path = os.path.join(self.download_dir, *result['path'])
                    print(f"{Fore.YELLOW}Downloading entire folder: {' > '.join(result['path'])}{Style.RESET_ALL}")
                    await self.download_folder(session, result['url'], folder_path, concurrency)
                    break

        print(f"{Fore.GREEN}Download process completed.{Style.RESET_ALL}")