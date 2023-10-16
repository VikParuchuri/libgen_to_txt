import argparse
import json
import re

import putiopy
import shutil
import subprocess
import time
import os
import pymysql.cursors
import magic
from clean_pdf import pdf_to_text
from clean_other import parse_epub, parse_djvu
from tqdm.contrib.concurrent import process_map
from settings import settings


def delete_file_locally(fpath):
    local_path = f"{settings.BASE_STORAGE_FOLDER}/{fpath}"
    shutil.rmtree(local_path)


def get_leading_digits(s):
    s = s.strip()
    match = re.match(r'^(\d+)', s)

    if match:
        return match.group(1)
    return


def get_file_path(num, client):
    files = client.File.list()
    try:
        sel_file = [f for f in files if get_leading_digits(f.name) == num][0]
    except IndexError:
        return
    return sel_file


def download_folder_locally(fpath):
    local_path = f"{settings.BASE_STORAGE_FOLDER}/{fpath}"
    # Need to configure rclone first
    command = ["rclone", "copy", f"{settings.RCLONE_ADAPTER_NAME}:{fpath}", local_path]
    subprocess.run(command)
    return local_path


def query_metadata(fmd5):
    connection = pymysql.connect(host='localhost',
                                 user=settings.LIBGEN_DB_USER,
                                 password=settings.LIBGEN_DB_PASS,
                                 database=settings.LIBGEN_DB_NAME,
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT ue.ID, ue.Title, ue.Author, ue.Year, ue.Language, ue.Publisher, ue.Topic, ue.Extension, ue.Cleaned, ue.Scanned, ue.Pages, de.descr, de.toc from updated_edited ue left outer join description_edited de on de.md5 = ue.MD5 where ue.MD5=%s order by ue.TimeLastModified desc limit 1;"
            cursor.execute(sql, (fmd5,))
            metadata = cursor.fetchone()

    return metadata

def find_filetype(fpath):
    mimetype = magic.from_file(fpath).lower()

    if "pdf" in mimetype:
        return "pdf"
    elif "epub" in mimetype:
        return "epub"
    elif "djvu" in mimetype:
        return "djvu"
    else:
        print(f"Found nonstandard filetype {mimetype}")
        return "other"


def process_single_file(fmd5, in_folder_path, out_folder_path):
    filepath = os.path.join(in_folder_path, fmd5)
    filetype = find_filetype(filepath)

    match(filetype):
        case "pdf":
            text = pdf_to_text(filepath)
        case "epub":
            text = parse_epub(filepath)
        case "djvu":
            text = parse_djvu(filepath)
        case _:
            return

    metadata = query_metadata(fmd5)
    if metadata is None:
        metadata = {}
    metadata_filepath = os.path.join(out_folder_path, f"{fmd5}_meta.json")

    out_filepath = os.path.join(out_folder_path, f"{fmd5}")
    with open(out_filepath, "w+") as f:
        f.write(text)

    with open(metadata_filepath, "w+") as f:
        f.write(json.dumps(metadata))


def process_batch_files(filenames, in_folder_path, out_folder_path):
    for fmd5 in filenames:
        try:
            process_single_file(fmd5, in_folder_path, out_folder_path)
        except Exception as e:
            print(f"Failed to process {fmd5}: {e}")


def download_folder(url, num, client):
    transfer = client.Transfer.add_url(url)

    iterations = 0
    sel_file = None
    sleep_interval = 60
    max_iterations = settings.MAX_TIME_TO_WAIT // sleep_interval
    while not sel_file and iterations < max_iterations:
        time.sleep(sleep_interval)
        iterations += 1
        sel_file = get_file_path(num, client)

    # Cancel the transfer
    transfer.cancel()
    # We didn't download the file
    if iterations >= max_iterations:
        return

    return sel_file


def process_single_chunk(torrent_info, max_workers=settings.CONVERSION_WORKERS):
    num, url = torrent_info

    client = putiopy.Client(settings.PUTIO_TOKEN, timeout=15, use_retry=True)
    sel_file = get_file_path(num, client)

    if not sel_file:
        sel_file = download_folder(url, num, client)
        if not sel_file:
            print(f"Failed to download {num}, or took too long")
            return

    stored_path = download_folder_locally(sel_file.name)
    files = os.listdir(stored_path)

    out_path = os.path.join(settings.BASE_TXT_FOLDER, num)
    os.makedirs(out_path, exist_ok=True)

    batches = [files[i:i + settings.BATCH_SIZE] for i in range(0, len(files), settings.BATCH_SIZE)]

    process_map(process_batch_files, batches, [stored_path] * len(batches), [out_path] * len(batches),
                max_workers=max_workers, chunksize=10, desc=f"Processing {num} into txt")

    # Mark that we have processed this segment of libgen
    with open(os.path.join(settings.BASE_PROCESSED_FOLDER, num), "w+") as f:
        f.write(sel_file.name)

    # Delete files from remote and local
    sel_file.delete()
    delete_file_locally(sel_file.name)


def process_single_chunk_wrapped(torrent_info):
    try:
        process_single_chunk(torrent_info)
    except Exception as e:
        print(f"Failed to process {torrent_info}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and process libgen")
    parser.add_argument("--max", type=int, default=None, help="Maximum number of chunks to process, for testing")
    parser.add_argument("--workers", type=int, default=settings.DOWNLOAD_WORKERS, help="Number of workers to use when downloading")
    args = parser.parse_args()

    os.makedirs(settings.BASE_STORAGE_FOLDER, exist_ok=True)
    os.makedirs(settings.BASE_PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(settings.BASE_TXT_FOLDER, exist_ok=True)

    torrent_url = "https://libgen.rs/repository_torrent/r_{num}.torrent"

    # TODO: improve logic for finding all torrent urls
    nums = [str(i) for i in range(1000, 4041000, 1000)]
    torrent_urls = []
    for num in nums:
        url = torrent_url.format(num=num)
        # Skip what we have processed
        if not os.path.exists(os.path.join(settings.BASE_PROCESSED_FOLDER, num)):
            torrent_urls.append((num, url))

    if args.max is not None:
        torrent_urls = torrent_urls[:args.max]

    process_map(process_single_chunk_wrapped, torrent_urls, max_workers=args.workers, chunksize=1, desc="Downloading and processing libgen")

