# Libgen to txt

This repo will convert books from libgen to plain txt or markdown format.  This repo does not contain any books, only the scripts to download and convert them.

The scripts use a seedbox to download the libgen torrents, copy them to your machine/cloud instance, convert them, and enrich them with metadata.  Processing will be by chunk, with configurable parallelization.

It currently only works for the libgen rs nonfiction section, but PRs welcome for additional compatibility.  It will cost about $300 to convert all of libgen rs nonfiction if you're using a cloud instance, and take about 1 week to process everything (bandwidth-bound).  You'll need 3TB of disk space.

## Community

[Discord](https://discord.gg//KuZwXNGnfH) is where we discuss future development.

# Install

This was only tested on Ubuntu 23.04 and Python 3.11.  It should work with Python 3.8+.

## Setup dependencies

- `apt-get update`
- `xargs apt-get install -y < apt-requirements.txt`
- `pip install -r requirements.txt`

## Import libgen rs metadata

- Download [the metadata DB](https://annas-archive.org/datasets/libgen_rs) (look for "metadata" and the nonfiction one)
- `bsdtar -xf libgen.rar`
- Start mariadb
  - `systemctl start mariadb.service`
- Setup DB user
  - `mariadb`
  - `GRANT ALL ON *.* TO 'libgen'@'localhost' IDENTIFIED BY 'password' WITH GRANT OPTION;` # Replace with your password
  - `FLUSH PRIVILEGES;`
  - `create database libgen;`
  - `exit`
- Import metadata
  - `git clone https://annas-software.org/AnnaArchivist/annas-archive.git`
  - `pv libgen.sql  | PYTHONIOENCODING=UTF8:ignore python3 annas-archive/data-imports/scripts/helpers/sanitize_unicode.py | mariadb -h localhost --default-character-set=utf8mb4 -u libgen -ppassword libgen`
    - You may need to add the `--binary-mode -o` flag to the `mariadb` command above
    - And the `--force` flag if you get errors

## Setup seedbox

- Make an account on [put.io](https://put.io)
- Install rclone following [these instructions](https://rclone.org/install/)
- Create a [putio adapter](https://rclone.org/putio/) for rclone

# Configuration

- Get a putio oauth token following [these instructions](https://help.put.io/en/articles/5972538-how-to-get-an-oauth-token-from-put-io)
- Either set the env var `PUTIO_TOKEN`, or create a `local.env` file with `PUTIO_TOKEN=yourtoken`
- Inspect `libgen_to_txt/settings.py`.  You can edit settings directly to override them, set an env var, or add the key to a `local.env` file.
  - You may particularly want to look at `CONVERSION_WORKERS` and `DOWNLOAD_WORKERS` to control parallelization.  The download step is the limiting factor, and too many download workers will saturate your bandwidth.

# Usage

- `python download_and_clean.py` to download and clean the data
  - `--workers` to control number of download workers (how many parallel downloads happen at once)
  - `--no_download` to only process libgen chunks that already exist on the seedbox
  - `--max` controls how many chunks at most to process (for testing)
  - `--no_local_delete` to avoid deleting chunks locally after they're downloaded.  Mainly useful for debugging.

You should see progress information printed out - it will take several weeks to finish depending on bandwidth and conversion method (see below).  Check the `txt` and `processed` folders to monitor.

## Markdown conversion

This can optionally be integrated with [marker](https://www.github.com/VikParuchuri/marker) to do high-accuracy pdf to markdown conversion.  To use marker, first install it, then:

- `CONVERSION_METHOD` to `marker`
- `MARKER_FOLDER` to the path to the marker folder

`CONVERSION_WORKERS` will control how many marker processes per GPU are run in parallel.  Marker takes about 2.5GB of VRAM per process, so set this accordingly.

You can adjust additional settings around how marker is integrated using the `MARKER_*` settings.  In particular, pay attention to the timeouts.  These ensure that conversion doesn't get stuck on a chunk. Marker can run on CPU or GPU, but is much faster on GPU.  With 4x GPUs, a single libgen chunk should take about 1 hour to process.

# Cloud storage

You can store the converted txt/markdown files in a s3-compatible storage backend as they're processed using `s3fs`.  Here's how:

- `sudo apt install s3fs`
- `echo ACCESS_KEY_ID:SECRET_ACCESS_KEY > ${HOME}/.passwd-s3fs`
- `chmod 600 ${HOME}/.passwd-s3fs`
- `s3fs BUCKET_NAME LOCAL_DIR -o url=STORAGE_URL -o use_cache=/tmp -o allow_other -o use_path_request_style -o uid=1000 -o gid=1000 -o passwd_file=${HOME}/.passwd-s3fs`