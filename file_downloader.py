import aiohttp
import os
from tqdm.asyncio import tqdm as tqdm_asyncio
import logging
import asyncio
import sys
import time
from colorama import Fore, Style

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

terminate = False
skip_current = False

def set_terminate_flag(value):
    global terminate
    terminate = value

def set_skip_flag(value):
    global skip_current
    skip_current = value

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:.0f}m {seconds:.0f}s"
    else:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:.0f}h {minutes:.0f}m {seconds:.0f}s"

async def download_file(session, url, path, expected_size, retries=10, backoff_factor=5):
    global terminate, skip_current
    if terminate:
        return None

    temp_path = f"{path}.tmp"
    existing_file_size = 0
    if os.path.exists(temp_path):
        existing_file_size = os.path.getsize(temp_path)
        logging.info(f"Found existing partial download: {url} ({existing_file_size} bytes)")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    progress_bar = None

    for attempt in range(retries):
        if terminate:
            return None

        try:
            logging.info(f"Downloading: {url} (Attempt {attempt + 1}/{retries})")
            timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour timeout

            if existing_file_size > 0:
                headers['Range'] = f"bytes={existing_file_size}-"
                logging.info(f"Attempting to resume download from byte {existing_file_size}")

            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(connector=connector) as retry_session:
                async with retry_session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status == 416:
                        logging.info(f"File already fully downloaded: {path}")
                        if os.path.exists(temp_path):
                            os.replace(temp_path, path)
                        return path, 0, 0  # Return path, 0 download time, and 0 speed
                    
                    if response.status == 429:
                        wait_time = backoff_factor * (2 ** attempt)
                        logging.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying.")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    if existing_file_size > 0 and response.status == 200:
                        logging.warning("Server does not support range requests. Starting download from the beginning.")
                        existing_file_size = 0

                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    if total_size == 0:
                        total_size = expected_size
                    if existing_file_size > 0 and response.status == 206:
                        total_size += existing_file_size
                    logging.info(f"Total file size: {total_size} bytes")
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    
                    mode = 'ab' if existing_file_size > 0 and response.status == 206 else 'wb'
                    
                    with open(temp_path, mode) as file:
                        if progress_bar is None:
                            progress_bar = tqdm_asyncio(
                                total=total_size,
                                initial=existing_file_size,
                                unit='iB',
                                unit_scale=True,
                                unit_divisor=1024,
                                desc=os.path.basename(path),
                                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]'
                            )
                        last_update_time = time.time()
                        last_size = existing_file_size
                        start_time = time.time()
                        inactivity_timer = 0
                        eta = 0
                        try:
                            async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                                if terminate:
                                    logging.info(f"Download interrupted: {os.path.basename(path)}")
                                    progress_bar.close()
                                    return None
                                if skip_current:
                                    logging.info(f"Skipping download: {os.path.basename(path)}")
                                    progress_bar.close()
                                    return "skipped"
                                if chunk:
                                    file.write(chunk)
                                    progress_bar.update(len(chunk))
                                    current_time = time.time()
                                    if current_time - last_update_time > 1:  # Update ETA every second
                                        current_size = file.tell()
                                        speed = (current_size - last_size) / (current_time - last_update_time)
                                        if speed > 0:
                                            eta = (total_size - current_size) / speed
                                        else:
                                            eta = 0
                                        if current_size == last_size:
                                            inactivity_timer += current_time - last_update_time
                                            if inactivity_timer >= 30:  # 30 seconds of inactivity
                                                logging.warning("Download seems to be stuck. Restarting...")
                                                raise aiohttp.ClientPayloadError("Download stuck")
                                        else:
                                            inactivity_timer = 0
                                        last_size = current_size
                                        last_update_time = current_time
                                        progress_bar.set_postfix_str(f"ETA: {format_time(eta)} | Inactive: {format_time(inactivity_timer)}", refresh=False)
                                else:
                                    logging.warning("Received empty chunk")
                                sys.stdout.flush()
                        except aiohttp.ClientPayloadError as e:
                            logging.error(f"Payload error during download: {e}")
                            if file.tell() < total_size:
                                logging.info("Download incomplete. Will retry from current position.")
                                raise
                        except asyncio.CancelledError:
                            logging.info(f"Download cancelled: {os.path.basename(path)}")
                            progress_bar.close()
                            return None
                        except Exception as e:
                            logging.error(f"Error during download: {e}")
                            raise
                        finally:
                            progress_bar.close()
                            end_time = time.time()
                            download_time = end_time - start_time
                            logging.info(f"Download attempt completed in {download_time:.2f} seconds")
                    
                    if os.path.getsize(temp_path) == total_size or total_size == 0:
                        os.replace(temp_path, path)
                        logging.info(f"Successfully downloaded: {path}")
                        size_mb = os.path.getsize(path) / (1024 * 1024)
                        speed_mbps = size_mb / download_time if download_time > 0 else 0
                        return path, download_time, speed_mbps
                    else:
                        logging.warning(f"Download incomplete. File size: {os.path.getsize(temp_path)}, Expected: {total_size}")
                        return None
        except aiohttp.ClientResponseError as e:
            if e.status == 416:
                logging.info(f"File already fully downloaded: {path}")
                if os.path.exists(temp_path):
                    os.replace(temp_path, path)
                return path, 0, 0  # Return path, 0 download time, and 0 speed
            logging.error(f"Client response error: {e}")
        except aiohttp.ClientError as e:
            logging.error(f"Client error during download: {e}")
        except asyncio.TimeoutError:
            logging.error("Download timed out")
        except OSError as e:
            logging.error(f"OS error during download: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during download: {e}")
        
        if attempt < retries - 1:
            wait_time = backoff_factor * (2 ** attempt)
            logging.info(f"Retrying download in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        else:
            logging.error(f"Failed to download file after {retries} attempts.")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    return None