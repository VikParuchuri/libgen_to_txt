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
        elif metadata["Extension"].strip() not in settings.MARKER_SUPPORTED_EXTENSIONS:
            os.unlink(fpath)
        else:
            all_metadata[fname] = {k.lower(): v for k, v in metadata.items()}
    return all_metadata


def marker_cpu(stored_path, out_path, metadata_file, max_workers):
    # Do not recommend using marker on CPU, will be very slow for libgen
    marker_dir = os.path.abspath(settings.MARKER_FOLDER)
    command = ["python", "convert.py", stored_path, out_path, "--workers", str(max_workers), "--metadata_file", metadata_file, "--min_length", str(settings.MARKER_MIN_LENGTH)]
    subprocess.run(command, timeout=settings.MARKER_CPU_TIMEOUT, cwd=marker_dir, shell=True, check=True)


def marker_gpu(stored_path, out_path, metadata_file, max_workers):
    marker_dir = os.path.abspath(settings.MARKER_FOLDER)
    command = f"poetry run bash chunk_convert.sh {stored_path} {out_path}"
    print(marker_dir)
    print(command)
    poetry_path = os.path.expanduser(settings.POETRY_DIR)
    full_path = os.environ['PATH'] + os.pathsep + poetry_path
    env = {
        "MIN_LENGTH": str(settings.MARKER_MIN_LENGTH),
        "METADATA_FILE": metadata_file,
        "NUM_DEVICES": str(settings.GPU_COUNT),
        "NUM_WORKERS": str(max_workers),
        "PATH": full_path
    }

    if settings.MARKER_DEBUG_DATA_FOLDER:
        env["DEBUG_DATA_FOLDER"] = settings.MARKER_DEBUG_DATA_FOLDER

    subprocess.run(command, timeout=settings.MARKER_GPU_TIMEOUT, env=env, cwd=marker_dir, shell=True, check=True)


def process_folder_marker(stored_path, out_path, num, max_workers):
    metadata = filter_invalid(stored_path)
    metadata_file = os.path.join(settings.BASE_METADATA_FOLDER, f"{num}_meta.json")

    with open(metadata_file, "w+") as f:
        json.dump(metadata, f)

    if settings.GPU_COUNT == 0:
        marker_cpu(stored_path, out_path, metadata_file, max_workers)
    else:
        marker_gpu(stored_path, out_path, metadata_file, max_workers)
