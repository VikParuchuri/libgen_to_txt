import fitz as pymupdf

from collections import defaultdict
from sklearn.cluster import DBSCAN
import numpy as np


def categorize_blocks(blocks, page_count):
    X = np.array(
        [(x0, y0, x1, y1, len(text)) for x0, y0, x1, y1, text in blocks]
    )

    dbscan = DBSCAN(eps=.1, min_samples=5)
    dbscan.fit(X)
    labels = dbscan.labels_
    label_chars = defaultdict(int)
    for i, label in enumerate(labels):
        label_chars[label] += len(blocks[i][-1])

    most_common_label = None
    most_chars = 0
    for i in label_chars.keys():
        if label_chars[i] > most_chars:
            most_common_label = i
            most_chars = label_chars[i]

    labels = [0 if label == most_common_label else 1 for label in labels]
    return labels


def calc_rect_center(rect, reverse_y=False):
    if reverse_y:
        x0, y0, x1, y1 = rect[0], -rect[1], rect[2], -rect[3]
    else:
        x0, y0, x1, y1 = rect

    x_center = (x0 + x1) / 2
    y_center = (y0 + y1) / 2
    return (x_center, y_center)


def pdf_to_text(pdf_path: str):
    rect_centers = []
    rects = []
    visual_label_texts = []
    categorize_vectors = []

    page_count = 0
    with pymupdf.open(pdf_path) as doc:
        for page_idx, page in enumerate(doc):
            page_count += 1
            blocks = page.get_text("blocks", sort=True, flags=~pymupdf.TEXT_PRESERVE_LIGATURES & pymupdf.TEXT_PRESERVE_WHITESPACE & ~pymupdf.TEXT_PRESERVE_IMAGES & ~pymupdf.TEXT_INHIBIT_SPACES & pymupdf.TEXT_DEHYPHENATE & pymupdf.TEXT_MEDIABOX_CLIP)
            for block_idx, block in enumerate(blocks):
                block_rect = block[:4]  # (x0,y0,x1,y1)
                rects.append(block_rect)
                block_text = block[4]

                rect_center = calc_rect_center(block_rect, reverse_y=True)
                rect_centers.append(rect_center)
                visual_label_texts.append(str(page_idx))

                categorize_vectors.append((*block_rect, block_text))

    labels = categorize_blocks(categorize_vectors, page_count)
    full_text = ""
    for i, rect_center in enumerate(rect_centers):
        text = categorize_vectors[i][-1]
        if labels[i] == 0:
            full_text += text
    return full_text

