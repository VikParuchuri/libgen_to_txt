from dotenv import find_dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Path settings
    BASE_STORAGE_FOLDER: str = "libgen" # temp storage for downloaded chunks
    BASE_PROCESSED_FOLDER: str = "processed" # After a chunk is processed, an empty file is created here
    BASE_TXT_FOLDER: str = "txt" # Where the final text is stored

    # Database
    LIBGEN_DB_NAME: str = "libgen"
    LIBGEN_DB_USER: str = "libgen"
    LIBGEN_DB_PASS: str = "password"

    # Download settings
    BATCH_SIZE: int = 100 # Number of pdfs to process in a single worker
    CONVERSION_WORKERS: int = 4 # Number of workers to use to convert pdfs for each libgen chunk
    DOWNLOAD_WORKERS: int = 40 # Number of download workers (bandwidth-bound)
    MAX_TIME_TO_WAIT: int = 60 * 60 * 6  # 6 hours to wait for a download to finish
    RCLONE_ADAPTER_NAME: str = "putio"

    # Put io
    PUTIO_TOKEN: str = ""

    class Config:
        env_file = find_dotenv("local.env")


settings = Settings()
