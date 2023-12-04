from libgen_to_txt.settings import settings
import os
import shutil
import subprocess
import time
import re


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


def download_folder(url, num, client, no_download=False):
    transfer = None
    if not no_download:
        transfer = client.Transfer.add_url(url)

    iterations = 0
    sel_file = None
    sleep_interval = 60
    max_iterations = settings.MAX_TIME_TO_WAIT // sleep_interval
    while not sel_file and iterations < max_iterations:
        time.sleep(sleep_interval)
        iterations += 1
        sel_file = get_file_path(num, client)

        # Don't wait if we are not downloading
        if no_download:
            break

    if transfer:
        # Cancel the transfer
        transfer.cancel()

    # We didn't download the file
    if iterations >= max_iterations:
        return

    return sel_file