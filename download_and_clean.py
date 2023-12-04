import argparse
import json
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

import putiopy
import os
from tqdm import tqdm

from libgen_to_txt.files import get_file_path, download_folder, download_folder_locally, delete_file_locally
from libgen_to_txt.metadata import batch_write_metadata
from libgen_to_txt.naive.convert import process_batch_files_naive
from libgen_to_txt.settings import settings


def process_single_libgen_chunk(torrent_info, conversion_lock, no_download, max_workers=settings.CONVERSION_WORKERS):
    num, url = torrent_info

    client = putiopy.Client(settings.PUTIO_TOKEN, timeout=15, use_retry=True)
    sel_file = get_file_path(num, client)

    if not sel_file:
        sel_file = download_folder(url, num, client, no_download)
        if not sel_file:
            print(f"Failed to download {num}, or took too long")
            return

    stored_path = download_folder_locally(sel_file.name)
    files = os.listdir(stored_path)

    out_path = os.path.join(settings.BASE_TXT_FOLDER, num)
    os.makedirs(out_path, exist_ok=True)

    match settings.CONVERSION_METHOD:
        case "naive":
            # PDF -> markdown
            process_batch_files_naive(files, stored_path, out_path, max_workers)
            # Write metadata
            batch_write_metadata(files, out_path, max_workers)
        case "marker":
            pass
        case _:
            print(f"Unknown conversion method {settings.CONVERSION_METHOD}")
            return

    # Mark that we have processed this segment of libgen
    with open(os.path.join(settings.BASE_PROCESSED_FOLDER, num), "w+") as f:
        f.write(sel_file.name)

    # Delete files from remote and local
    sel_file.delete()
    delete_file_locally(sel_file.name)


def try_process_single_libgen_chunk(torrent_info, lock, no_download=False):
    try:
        process_single_libgen_chunk(torrent_info, lock, no_download)
    except Exception as e:
        print(f"Failed to process {torrent_info}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and process libgen")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of chunks to process, for testing")
    parser.add_argument("--workers", type=int, default=settings.DOWNLOAD_WORKERS, help="Number of workers to use when downloading")
    parser.add_argument("--no_download", type=int, action="store_true", help="Only process what already exists on the seedbox", default=False)
    args = parser.parse_args()

    os.makedirs(settings.BASE_STORAGE_FOLDER, exist_ok=True)
    os.makedirs(settings.BASE_PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(settings.BASE_TXT_FOLDER, exist_ok=True)

    torrent_url = "https://libgen.rs/repository_torrent/r_{num}.torrent"

    # TODO: improve logic for finding all torrent urls
    nums = [str(i) for i in range(1000, 4143000, 1000)]
    torrent_urls = []
    for num in nums:
        url = torrent_url.format(num=num)
        # Skip what we have processed
        if not os.path.exists(os.path.join(settings.BASE_PROCESSED_FOLDER, num)):
            torrent_urls.append((num, url))

    if args.max is not None:
        torrent_urls = torrent_urls[:args.max]

    m = multiprocessing.Manager()
    lock = m.Lock()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tqdm(pool.map(try_process_single_libgen_chunk, torrent_urls, repeat(lock), repeat(args.no_download), chunksize=1), total=len(torrent_urls))
    pool.shutdown()

