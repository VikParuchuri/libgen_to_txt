import subprocess
import os
from libgen_to_txt.settings import settings

from libgen_to_txt.metadata import query_metadata
import json


def filter_invalid(folder_name):
    files = os.listdir(folder_name)
    all_metadata = {}
    for fname in files:
        if fname.startswith("."):
            continue
        fpath = os.path.join(folder_name, fname)
        metadata = query_metadata(fname)
        if not metadata:
            os.unlink(fpath)
            continue

        if metadata["Language"].strip() not in settings.MARKER_SUPPORTED_LANGUAGES:
            os.unlink(fpath)
        elif metadata["Extension"].strip() not in settings.MARLER_SUPPORTED_EXTENSIONS:
            os.unlink(fpath)
        else:
            all_metadata[fname] = {k.lower(): v for k, v in metadata.items()}
    return all_metadata


def marker_cpu(stored_path, out_path, metadata_file, max_workers):
    command = ["python", "convert.py", stored_path, out_path, "--workers", str(max_workers), "--metadata_file", metadata_file, "--min_length", str(settings.MARKER_MIN_LENGTH)]
    subprocess.run(command, timeout=settings.MARKER_TIMEOUT)


def marker_gpu(stored_path, out_path, metadata_file, max_workers):
    # MIN_LENGTH=10000 METADATA_FILE=../pdf_meta.json NUM_DEVICES=4 NUM_WORKERS=15 bash chunk_convert.sh ../pdf_in ../md_out
    command = ["bash", "chunk_convert.sh", stored_path, out_path]
    subprocess.run(command, timeout=settings.MARKER_TIMEOUT, env={"MIN_LENGTH": str(settings.MARKER_MIN_LENGTH), "METADATA_FILE": metadata_file, "NUM_DEVICES": str(settings.GPU_COUNT), "NUM_WORKERS": str(max_workers)})


def process_folder_marker(stored_path, out_path, num, max_workers):
    metadata = filter_invalid(stored_path)
    metadata_file = os.path.join(settings.BASE_METADATA_FOLDER, f"{num}_meta.json")

    with open(metadata_file, "w+") as f:
        json.dump(metadata, f)

    if settings.GPU_COUNT == 0:
        marker_cpu(stored_path, out_path, metadata_file, max_workers)
    else:
        marker_gpu(stored_path, out_path, metadata_file, max_workers)
