from collections import Counter
from libgen_to_txt.settings import settings
import fitz as pymupdf


def filter_common_elements(lines, page_count):
    text = [l for l in lines if len(l) > 4]
    counter = Counter(text)
    common = [k for k, v in counter.items() if v > page_count * .6]
    return common


def filter_header_footer(page_text_blocks, max_selected_lines=2):
    first_lines = []
    last_lines = []
    for page in page_text_blocks:
        page_first_lines = page[:max_selected_lines]
        page_last_lines = page[-max_selected_lines:]
        first_lines.extend(page_first_lines)
        last_lines.extend(page_last_lines)

    bad_lines = filter_common_elements(first_lines, len(page_text_blocks))
    bad_lines += filter_common_elements(last_lines, len(page_text_blocks))

    return bad_lines


def pdf_to_text(pdf_path: str):
    page_text_blocks = []
    with pymupdf.open(pdf_path) as doc:
        for page_idx, page in enumerate(doc):
            blocks = page.get_text("blocks", sort=True, flags=settings.TEXT_FLAGS)
            text_blocks = []
            for block_idx, block in enumerate(blocks):
                block_text = block[4]
                text_blocks.append(block_text)
            page_text_blocks.append(text_blocks)

    bad_text = filter_header_footer(page_text_blocks)
    full_text = ""
    for page in page_text_blocks:
        for block in page:
            if block not in bad_text:
                full_text += block + "\n"
    return full_text