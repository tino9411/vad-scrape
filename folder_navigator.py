import os
import asyncio
from colorama import Fore, Style

class FolderNavigator:
    def __init__(self, base_scraper):
        self.scraper = base_scraper
        self.current_path = "/"
        self.history = []

    async def list_contents(self):
        return await self.scraper.fetch_directory_contents(self.current_path)

    def change_directory(self, new_dir):
        self.history.append(self.current_path)
        self.current_path = os.path.normpath(os.path.join(self.current_path, new_dir))

    def go_back(self):
        if self.history:
            self.current_path = self.history.pop()
        else:
            print(f"{Fore.YELLOW}Already at the root directory.{Style.RESET_ALL}")

    async def navigate(self):
        while True:
            contents = await self.list_contents()
            print(f"\n{Fore.CYAN}Current path: {self.current_path}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}")
            
            for i, item in enumerate(contents, 1):
                icon = "📁" if item['is_dir'] else "📄"
                print(f"{i:2}. {icon} {item['name']}")
            
            print(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Commands: 'q' to quit, '..' to go up, 'b' to go back{Style.RESET_ALL}")
            choice = input(f"{Fore.CYAN}Enter your choice: {Style.RESET_ALL}")

            if choice.lower() == 'q':
                break
            elif choice == '..':
                self.change_directory('..')
            elif choice.lower() == 'b':
                self.go_back()
            elif choice.isdigit() and 1 <= int(choice) <= len(contents):
                selected = contents[int(choice) - 1]
                if selected['is_dir']:
                    self.change_directory(selected['name'])
                else:
                    await self.handle_file_selection(selected)
            else:
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

    async def handle_file_selection(self, file):
        print(f"\n{Fore.GREEN}Selected file: {file['name']}{Style.RESET_ALL}")
        choice = input(f"{Fore.YELLOW}Do you want to download this file? (y/n): {Style.RESET_ALL}").lower()
        if choice == 'y':
            await self.scraper.download_item(file['url'], self.current_path, file['name'])
        else:
            print(f"{Fore.YELLOW}Download cancelled.{Style.RESET_ALL}")

    async def search(self, query):
        results = await self.scraper.search_in_directory(self.current_path, query)
        if results:
            print(f"\n{Fore.GREEN}Search results for '{query}':{Style.RESET_ALL}")
            for i, result in enumerate(results, 1):
                icon = "📁" if result['is_dir'] else "📄"
                print(f"{i:2}. {icon} {result['name']} ({result['path']})")
            
            choice = input(f"{Fore.YELLOW}Enter number to navigate to item, or press Enter to cancel: {Style.RESET_ALL}")
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                selected = results[int(choice) - 1]
                if selected['is_dir']:
                    self.current_path = selected['path']
                else:
                    self.current_path = os.path.dirname(selected['path'])
                    await self.handle_file_selection(selected)
        else:
            print(f"{Fore.YELLOW}No results found for '{query}'{Style.RESET_ALL}")

    async def run(self):
        while True:
            print(f"\n{Fore.CYAN}Folder Navigation Menu:{Style.RESET_ALL}")
            print(f"1. Browse folders")
            print(f"2. Search in current directory")
            print(f"3. Return to main menu")
            choice = input(f"{Fore.YELLOW}Enter your choice: {Style.RESET_ALL}")

            if choice == '1':
                await self.navigate()
            elif choice == '2':
                query = input(f"{Fore.YELLOW}Enter search query: {Style.RESET_ALL}")
                await self.search(query)
            elif choice == '3':
                break
            else:
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")