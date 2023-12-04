import magic


def find_filetype(fpath):
    mimetype = magic.from_file(fpath).lower()

    if "pdf" in mimetype:
        return "pdf"
    elif "epub" in mimetype:
        return "epub"
    elif "djvu" in mimetype:
        return "djvu"
    elif "mobi" in mimetype:
        return "mobi"
    else:
        print(f"Found nonstandard filetype {mimetype}")
        return "other"