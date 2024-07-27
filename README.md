# VadScrape - Video Content Downloader

VadScrape is a Python-based command-line tool designed to search and download TV shows and movies from specified online sources. It provides a user-friendly interface for searching content, selecting specific seasons or episodes, and managing downloads with resume capability.

## Features

- Search and download TV shows and movies
- Support for multiple seasons and episodes
- Download resume functionality for interrupted downloads
- Option for sequential or concurrent downloads
- Detailed download history and progress tracking
- Configurable download paths for different content types
- Color-coded console output for better readability

## Requirements

- Python 3.7+
- aiohttp
- beautifulsoup4
- colorama
- tqdm

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/vadscrape.git
   cd vadscrape
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Configure the `config.json` file with your preferred download paths:
   ```json
   {
     "base_url": "https://vadapav.mov",
     "download_paths": {
       "TV Shows": "/path/to/your/tv/shows/directory",
       "Movies": "/path/to/your/movies/directory",
       "Anime": "/path/to/your/anime/directory"
     }
   }
   ```

## Usage

Run the main script:

```
python app.py
```

Follow the on-screen prompts to:
1. Choose between TV shows and movies
2. Enter a search query
3. Select the content you want to download
4. For TV shows, choose specific seasons or download all
5. Set the concurrency level for downloads (1 for sequential, 2+ for concurrent)

The program will handle the rest, downloading the selected content to the configured directories.

## Features in Detail

- **Sequential Downloads**: By default, the tool uses sequential downloads for optimal performance and stability.
- **Concurrent Downloads**: Users can opt for concurrent downloads by setting a concurrency level greater than 1. This may be useful in some network environments but could potentially slow down overall download speed.
- **Resume Functionality**: If a download is interrupted, the tool will attempt to resume from where it left off.
- **Download History**: The tool maintains a history of downloaded content, allowing you to track what you've already downloaded.
- **Error Handling**: Robust error handling ensures the tool can recover from network issues or interrupted downloads.

## Configuration

You can modify the `config.json` file to change:
- The base URL for content
- Download paths for different types of content

## Troubleshooting

If you encounter any issues:
1. Check your internet connection
2. Ensure you have write permissions in the configured download directories
3. Verify that the `config.json` file is correctly formatted
4. Check the console output for any error messages
5. If downloads are slow, try using a concurrency level of 1 (sequential downloads)

## Disclaimer

This tool is for educational purposes only. Ensure you have the right to download and store the content you're accessing. The authors are not responsible for any misuse of this tool.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).