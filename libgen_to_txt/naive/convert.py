from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

from libgen_to_txt.naive.other import parse_epub, parse_djvu
from libgen_to_txt.naive.pdf import pdf_to_text
import os

from libgen_to_txt.util import find_filetype


def process_single_file(fmd5, in_folder_path, out_folder_path):
    filepath = os.path.join(in_folder_path, fmd5)
    filetype = find_filetype(filepath)
    out_filepath = os.path.join(out_folder_path, f"{fmd5}")

    convert(filepath, filetype, out_filepath)


def try_process_single_file(fmd5, in_folder_path, out_folder_path):
    try:
        process_single_file(fmd5, in_folder_path, out_folder_path)
    except Exception as e:
        print(f"Failed to process {fmd5}: {e}")


def process_batch_files_naive(files, stored_path, out_path, max_workers):
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(try_process_single_file, files, repeat(stored_path), repeat(out_path), chunksize=10)


def convert(filepath, filetype, out_filepath):
    match (filetype):
        case "pdf":
            text = pdf_to_text(filepath)
        case "epub":
            text = parse_epub(filepath)
        case "djvu":
            text = parse_djvu(filepath)
        case _:
            return

    with open(out_filepath, "w+") as f:
        f.write(text)
