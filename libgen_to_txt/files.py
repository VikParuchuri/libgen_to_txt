from typing import Optional

from libgen_to_txt.settings import settings
import shutil
import subprocess
import time
import re


def get_parent_id(client):
    folder_name = settings.PUTIO_FOLDER
    if not folder_name:
        return 0
    folders = [n for n in client.File.list() if n.name == "libgen"]
    if len(folders) == 0:
        return 0

    folder = folders[0]
    return folder.id


def delete_file_locally(fpath):
    local_path = f"{settings.BASE_STORAGE_FOLDER}/{fpath}"
    shutil.rmtree(local_path)


def get_leading_digits(s):
    s = s.strip()
    match = re.match(r'^(\d+)', s)

    if match:
        return match.group(1)
    return


def get_file_path(num, client, parent_id):
    files = client.File.list(parent_id=parent_id)
    try:
        sel_file = [f for f in files if get_leading_digits(f.name) == num][0]
    except IndexError:
        return
    return sel_file


def download_folder_locally(fpath):
    putio_path = fpath
    if settings.PUTIO_FOLDER:
        putio_path = f"{settings.PUTIO_FOLDER}/{fpath}"

    local_path = f"{settings.BASE_STORAGE_FOLDER}/{fpath}"
    # Need to configure rclone first
    command = ["rclone", "copy", f"{settings.RCLONE_ADAPTER_NAME}:{putio_path}", local_path]
    subprocess.run(command)
    return local_path


def download_folder(url, num, client, parent_folder_id, no_download=False):
    transfer = None
    if not no_download:
        transfer = client.Transfer.add_url(url, parent_id=parent_folder_id)

    iterations = 0
    sel_file = None
    sleep_interval = 60
    max_iterations = settings.MAX_TIME_TO_WAIT // sleep_interval

    # If we're not downloading, don't need to wait
    if no_download:
        sel_file = get_file_path(num, client, parent_folder_id)
    else:
        # Wait for the file to be downloaded
        while not sel_file and iterations < max_iterations:
            time.sleep(sleep_interval)
            sel_file = get_file_path(num, client, parent_folder_id)
            iterations += 1

    if transfer:
        # Cancel the transfer
        transfer.cancel()

    return sel_file