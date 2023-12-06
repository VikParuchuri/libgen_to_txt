import argparse
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

import putiopy
import os
from tqdm import tqdm

from libgen_to_txt.files import get_file_path, download_folder, download_folder_locally, delete_file_locally, \
    get_parent_id
from libgen_to_txt.marker.convert import process_folder_marker
from libgen_to_txt.metadata import batch_write_metadata
from libgen_to_txt.naive.convert import process_batch_files_naive
from libgen_to_txt.settings import settings


def process_single_libgen_chunk(torrent_info, conversion_lock, no_download, no_delete, max_workers=settings.CONVERSION_WORKERS):
    num, url = torrent_info

    client = putiopy.Client(settings.PUTIO_TOKEN, timeout=15, use_retry=True)
    parent_folder_id = get_parent_id(client)
    sel_file = get_file_path(num, client, parent_folder_id)

    if not sel_file:
        sel_file = download_folder(url, num, client, parent_folder_id, no_download)
        if not sel_file:
            return

    stored_path = download_folder_locally(sel_file.name)
    files = os.listdir(stored_path)

    out_path = os.path.join(settings.BASE_TXT_FOLDER, num)
    os.makedirs(out_path, exist_ok=True)

    # Only one chunk can be converted at once
    with conversion_lock:
        match settings.CONVERSION_METHOD:
            case "naive":
                # PDF -> markdown
                process_batch_files_naive(files, stored_path, out_path, max_workers)
                # Write metadata
                batch_write_metadata(files, out_path, max_workers)
            case "marker":
                # PDF -> markdown
                process_folder_marker(stored_path, out_path, num, max_workers)
            case _:
                print(f"Unknown conversion method {settings.CONVERSION_METHOD}")
                return

    # Mark that we have processed this segment of libgen
    with open(os.path.join(settings.BASE_PROCESSED_FOLDER, num), "w+") as f:
        f.write(sel_file.name)

    # Delete files from remote and local
    if not no_download:
        sel_file.delete()

    if not no_delete:
        delete_file_locally(sel_file.name)


def try_process_single_libgen_chunk(torrent_info, lock, options):
    try:
        no_download = options["no_download"]
        no_delete = options["no_local_delete"]
        process_single_libgen_chunk(torrent_info, lock, no_download, no_delete)
    except Exception as e:
        print(f"Failed to process {torrent_info}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and process libgen")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of chunks to process, for testing")
    parser.add_argument("--workers", type=int, default=settings.DOWNLOAD_WORKERS, help="Number of workers to use when downloading")
    parser.add_argument("--no_download", action="store_true", help="Only process what already exists on the seedbox", default=False)
    parser.add_argument("--no_local_delete", action="store_true", help="Do not delete files locally", default=False)
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
    args_dict = vars(args)
    if args.workers == 1:
        for torrent_info in tqdm(torrent_urls):
            try_process_single_libgen_chunk(torrent_info, lock, args_dict)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            tqdm(pool.map(try_process_single_libgen_chunk, torrent_urls, repeat(lock), repeat(args_dict), chunksize=1), total=len(torrent_urls))

