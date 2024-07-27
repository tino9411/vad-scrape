import json
import os
import logging
from colorama import Fore, Style

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Config file not found. Creating a new one...")
        return create_config()
    except json.JSONDecodeError:
        logging.error("Invalid JSON in config file. Please check the format.")
        return None

def create_config():
    config = {
        "base_url": "https://vadapav.mov",
        "download_paths": {
            "TV Shows": os.path.expanduser("~/Videos/TV Shows"),
            "Movies": os.path.expanduser("~/Videos/Movies"),
            "Anime": os.path.expanduser("~/Videos/Anime")
        }
    }
    save_config(config)
    return config

def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def modify_config(config):
    print(f"\n{Fore.YELLOW}Current configuration:{Style.RESET_ALL}")
    print(f"Base URL: {config['base_url']}")
    for category, path in config['download_paths'].items():
        print(f"{category}: {path}")

    while True:
        print(f"\n{Fore.YELLOW}Options:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1. Change base URL{Style.RESET_ALL}")
        print(f"{Fore.CYAN}2. Modify existing category{Style.RESET_ALL}")
        print(f"{Fore.CYAN}3. Add new category{Style.RESET_ALL}")
        print(f"{Fore.CYAN}4. Remove category{Style.RESET_ALL}")
        print(f"{Fore.CYAN}5. Save and exit{Style.RESET_ALL}")

        choice = input(f"\n{Fore.YELLOW}Enter your choice (1-5): {Style.RESET_ALL}").strip()

        if choice == '1':
            config['base_url'] = input(f"{Fore.YELLOW}Enter new base URL: {Style.RESET_ALL}").strip()
        elif choice == '2':
            category = input(f"{Fore.YELLOW}Enter category name to modify: {Style.RESET_ALL}").strip()
            if category in config['download_paths']:
                new_path = input(f"{Fore.YELLOW}Enter new path for {category}: {Style.RESET_ALL}").strip()
                config['download_paths'][category] = os.path.expanduser(new_path)
            else:
                print(f"{Fore.RED}Category not found.{Style.RESET_ALL}")
        elif choice == '3':
            category = input(f"{Fore.YELLOW}Enter new category name: {Style.RESET_ALL}").strip()
            path = input(f"{Fore.YELLOW}Enter path for {category}: {Style.RESET_ALL}").strip()
            config['download_paths'][category] = os.path.expanduser(path)
        elif choice == '4':
            category = input(f"{Fore.YELLOW}Enter category name to remove: {Style.RESET_ALL}").strip()
            if category in config['download_paths']:
                del config['download_paths'][category]
            else:
                print(f"{Fore.RED}Category not found.{Style.RESET_ALL}")
        elif choice == '5':
            save_config(config)
            break
        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")

    return config