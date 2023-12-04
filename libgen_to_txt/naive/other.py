import subprocess

import ebooklib
import html2text as html2text
from ebooklib import epub


def parse_epub(path):
    book = epub.read_epub(path)
    markdown_content = ""

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            html_content = item.get_body_content().decode('utf-8')
            markdown_content += html2text.html2text(html_content)

    return markdown_content


def parse_djvu(path):
    stdout = None
    try:
        result = subprocess.run(["djvutxt", path], stdout=subprocess.PIPE, check=True, text=True)
        stdout = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
    except FileNotFoundError:
        print("Error: djvutxt utility not found. Ensure DjVuLibre is installed and added to your PATH.")
    return stdout