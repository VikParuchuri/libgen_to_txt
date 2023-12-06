from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

import pymysql

from libgen_to_txt.settings import settings
import os
import json


def batch_write_metadata(files, out_folder_path, max_workers):
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(try_write_metadata, files, repeat(out_folder_path), chunksize=10)


def try_write_metadata(fmd5, out_folder_path):
    try:
        write_metadata(fmd5, out_folder_path)
    except Exception as e:
        pass


def write_metadata(fmd5, out_folder_path):
    metadata = query_metadata(fmd5)
    if metadata is None:
        metadata = {}
    metadata_filepath = os.path.join(out_folder_path, f"{fmd5}_meta.json")

    with open(metadata_filepath, "w+") as f:
        f.write(json.dumps(metadata))


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