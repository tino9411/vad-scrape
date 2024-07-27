import asyncio
import logging
from colorama import init, Fore, Style
from config import load_config, modify_config
from scraper.tv_show_scraper import TVShowScraper
from scraper.movie_scraper import MovieScraper
from scraper.anime_scraper import AnimeScraper

# Initialize colorama
init(autoreset=True)

# Set up logging with colors
class ColoredFormatter(logging.Formatter):
    FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    FORMATS = {
        logging.DEBUG: Fore.CYAN + FORMAT + Style.RESET_ALL,
        logging.INFO: Fore.GREEN + FORMAT + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + FORMAT + Style.RESET_ALL,
        logging.ERROR: Fore.RED + FORMAT + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + FORMAT + Style.RESET_ALL,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

async def download_content(scraper, search_query, concurrency):
    if isinstance(scraper, AnimeScraper):
        await scraper.search_and_download(search_query, concurrency)
    else:
        await scraper.search_and_download(search_query, concurrency)

async def main():
    config = load_config()
    if not config:
        return

    while True:
        print(f"\n{Fore.YELLOW}Main Menu:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1. Search and download TV Show{Style.RESET_ALL}")
        print(f"{Fore.CYAN}2. Search and download Movie{Style.RESET_ALL}")
        print(f"{Fore.CYAN}3. Search and download Anime{Style.RESET_ALL}")
        print(f"{Fore.CYAN}4. View download history{Style.RESET_ALL}")
        print(f"{Fore.CYAN}5. Modify configuration{Style.RESET_ALL}")
        print(f"{Fore.CYAN}6. Quit{Style.RESET_ALL}")

        choice = input(f"\n{Fore.YELLOW}Enter your choice (1-6): {Style.RESET_ALL}").strip()

        if choice in ['1', '2', '3']:
            concurrency = 1
            if choice in ['1', '2']:
                concurrency_input = input(f"{Fore.YELLOW}Enter concurrency level (1 for sequential, 2+ for concurrent downloads): {Style.RESET_ALL}").strip()
                try:
                    concurrency = int(concurrency_input)
                    if concurrency < 1:
                        raise ValueError
                except ValueError:
                    print(f"{Fore.RED}Invalid concurrency level. Using default (1).{Style.RESET_ALL}")
                    concurrency = 1

            search_query = input(f"\n{Fore.YELLOW}Enter a search term: {Style.RESET_ALL}").strip()

            if choice == '1':
                scraper = TVShowScraper(config['base_url'], config['download_paths']['TV Shows'])
            elif choice == '2':
                scraper = MovieScraper(config['base_url'], config['download_paths']['Movies'])
            else:
                scraper = AnimeScraper(config['base_url'], config['download_paths']['Anime'])

            await download_content(scraper, search_query, concurrency)

        elif choice == '4':
            print(f"\n{Fore.YELLOW}Select history to view:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}1. TV Shows{Style.RESET_ALL}")
            print(f"{Fore.CYAN}2. Movies{Style.RESET_ALL}")
            print(f"{Fore.CYAN}3. Anime{Style.RESET_ALL}")
            history_choice = input(f"\n{Fore.YELLOW}Enter your choice (1-3): {Style.RESET_ALL}").strip()
            if history_choice == '1':
                tv_scraper = TVShowScraper(config['base_url'], config['download_paths']['TV Shows'])
                tv_scraper.display_download_history()
            elif history_choice == '2':
                movie_scraper = MovieScraper(config['base_url'], config['download_paths']['Movies'])
                movie_scraper.display_download_history()
            elif history_choice == '3':
                anime_scraper = AnimeScraper(config['base_url'], config['download_paths']['Anime'])
                anime_scraper.display_download_history()
            else:
                print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
        elif choice == '5':
            config = modify_config(config)
        elif choice == '6':
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

    print(f"{Fore.GREEN}Program terminated. Goodbye!{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())