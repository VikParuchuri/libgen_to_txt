from typing import List, Optional

from dotenv import find_dotenv
from pydantic_settings import BaseSettings
import fitz as pymupdf


class Settings(BaseSettings):
    # Path settings
    BASE_STORAGE_FOLDER: str = "libgen" # temp storage for downloaded chunks
    BASE_PROCESSED_FOLDER: str = "processed" # After a chunk is processed, an empty file is created here
    BASE_TXT_FOLDER: str = "txt" # Where the final text is stored
    BASE_METADATA_FOLDER: str = "metadata" # Where to store metadata for processing

    # Database
    LIBGEN_DB_NAME: str = "libgen"
    LIBGEN_DB_USER: str = "libgen"
    LIBGEN_DB_PASS: str = "password"

    # Download settings
    CONVERSION_WORKERS: int = 18 # Number of workers to use to convert pdfs for each libgen chunk
    DOWNLOAD_WORKERS: int = 8 # Number of download workers (bandwidth-bound)
    MAX_TIME_TO_WAIT: int = 60 * 60 * 6  # 6 hours to wait for a download to finish
    RCLONE_ADAPTER_NAME: str = "putio"

    # Conversion to markdown
    TEXT_FLAGS: int = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
    CONVERSION_METHOD: str = "naive" # Either naive or marker.  Naive is faster, but marker is more accurate.

    # Marker
    GPU_COUNT: int = 0 # Number of GPUs to use for marker.  0 means to use CPU only
    MARKER_FOLDER: str = "../marker"
    MARKER_GPU_TIMEOUT: int = 60 * 60 * 8 # Time to wait for marker gpu to finish
    MARKER_CPU_TIMEOUT: int = 60 * 60 * 24 # Time to wait for marker to finish
    MARKER_SUPPORTED_LANGUAGES: List = ["English", "Spanish", "Portuguese", "French", "German", "Russian"]
    MARKER_SUPPORTED_EXTENSIONS: List = ["pdf", "epub", "mobi", "xps", "fb2"]
    MARKER_MIN_LENGTH: int = 10000 # Min amount of text to extract from file naively before using marker
    MARKER_DEBUG_DATA_FOLDER: Optional[str] = None # Folder to store debug data in
    POETRY_DIR: str = "~/.local/bin" # Poetry directory, used to activate marker venv

    # Put io
    PUTIO_TOKEN: str = ""
    PUTIO_FOLDER: str = "libgen"

    class Config:
        env_file = find_dotenv("local.env")


settings = Settings()
