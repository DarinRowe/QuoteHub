#!/usr/bin/env python3
"""
Extract images from the Wang Xing PDF and map each to its entry number.

Saves images to:  wang-xing/images/entry_{entry_num}_{idx}.{ext}
Outputs a JSON map: wang-xing/images/map.json  { "entry_num": ["filename", ...] }

Usage: python3 extract_images.py
"""

import json
import os
import re
import sys
import fitz  # PyMuPDF

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PDF_PATH   = os.path.join(ROOT_DIR, "wang-xing",
                          "88万字，王兴饭否动态合集，2007年-2020年12月.pdf")
OUT_DIR    = os.path.join(ROOT_DIR, "wang-xing", "images")
MAP_PATH   = os.path.join(OUT_DIR, "map.json")

ENTRY_RE   = re.compile(r'^(\d+)\.\s*$|^(\d+)\.\s+\S')


def entry_num(m) -> int:
    """Extract entry number from ENTRY_RE match (handles two capture groups)."""
    return int(m.group(1) or m.group(2))

os.makedirs(OUT_DIR, exist_ok=True)


def page_entry_image_pairs(doc):
    """
    Yield (entry_num, xref, ext, image_bytes) for every image in the PDF.
    Entry num is determined by the last entry header seen before the image
    on the same page (by Y coordinate).
    """
    current_entry = 0  # global running counter across pages

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        # blocks: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type: 0=text, 1=image
        img_xrefs = {img[0]: True for img in page.get_images(full=True)}

        # Separate text and image blocks, sorted by Y
        text_blocks = sorted([b for b in blocks if b[6] == 0], key=lambda b: b[1])
        img_blocks  = sorted([b for b in blocks if b[6] == 1], key=lambda b: b[1])

        if not img_blocks:
            # Still advance current_entry by scanning text
            for tb in text_blocks:
                for line in tb[4].splitlines():
                    m = ENTRY_RE.match(line.strip())
                    if m:
                        current_entry = entry_num(m)
            continue

        # Build a Y-sorted list of (y, kind, data)
        # kind: 'entry' with entry_num, or 'image' with xref
        events = []
        for tb in text_blocks:
            for line in tb[4].splitlines():
                m = ENTRY_RE.match(line.strip())
                if m:
                    events.append((tb[1], 'entry', entry_num(m)))
        for ib in img_blocks:
            events.append((ib[1], 'image', None))  # xref resolved separately

        events.sort(key=lambda e: e[0])

        # Walk events; track last seen entry; assign images to entries
        img_iter = iter(img_blocks)
        last_entry = current_entry
        img_count_this_entry = {}

        for _, kind, val in events:
            if kind == 'entry':
                last_entry = val
                current_entry = val
            else:
                # This is an image block — get next image on this page
                try:
                    ib = next(img_iter)
                except StopIteration:
                    break
                # Find the xref for this image block by checking all page images
                # PyMuPDF image blocks don't carry xref directly; use page.get_images
                # We rely on order matching (image blocks appear in order)
                page_imgs = page.get_images(full=True)
                # Use a simple counter per page
                idx = img_count_this_entry.get(last_entry, 0)
                img_count_this_entry[last_entry] = idx + 1
                yield last_entry, idx, page_num, page


def extract_all():
    doc = fitz.open(PDF_PATH)
    img_map = {}  # entry_num (str) -> [filename, ...]

    # We need a reliable way to iterate images in page order matched to blocks.
    # Simpler approach: per page, sort image blocks by Y, get_images by order.
    current_entry = 0
    saved = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_imgs = page.get_images(full=True)

        # Use dict mode to get both text and image blocks with bounding boxes
        page_dict = page.get_text("dict")
        all_blocks = page_dict["blocks"]

        text_blocks = sorted([b for b in all_blocks if b["type"] == 0], key=lambda b: b["bbox"][1])
        img_blocks  = sorted([b for b in all_blocks if b["type"] == 1], key=lambda b: b["bbox"][1])

        if not img_blocks:
            # Advance entry counter
            for tb in text_blocks:
                for span in (s for line in tb.get("lines", []) for s in line.get("spans", [])):
                    m = ENTRY_RE.match(span["text"].strip())
                    if m:
                        current_entry = entry_num(m)
            continue

        # Build Y-ordered event list
        events = []
        for tb in text_blocks:
            y = tb["bbox"][1]
            for line in tb.get("lines", []):
                for span in line.get("spans", []):
                    m = ENTRY_RE.match(span["text"].strip())
                    if m:
                        events.append((y, 'entry', entry_num(m)))
        for i, ib in enumerate(img_blocks):
            events.append((ib["bbox"][1], 'image', i))

        events.sort(key=lambda e: e[0])

        last_entry = current_entry
        img_idx_counter = {}

        # page_imgs order matches image block order on page
        for _, kind, val in events:
            if kind == 'entry':
                last_entry = val
                current_entry = val
            else:
                block_idx = val
                if block_idx >= len(page_imgs):
                    continue
                xref = page_imgs[block_idx][0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                ext  = base_image["ext"]
                data = base_image["image"]

                count = img_idx_counter.get(last_entry, 0)
                img_idx_counter[last_entry] = count + 1

                fname = f"entry_{last_entry}_{count}.{ext}"
                fpath = os.path.join(OUT_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(data)

                key = str(last_entry)
                img_map.setdefault(key, []).append(fname)
                saved += 1

        if page_num % 100 == 0:
            print(f"  Page {page_num+1}/{len(doc)} — {saved} images saved so far",
                  flush=True)

    doc.close()

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(img_map, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {saved} images saved to {OUT_DIR}")
    print(f"Map written to {MAP_PATH}")
    print(f"Entries with images: {len(img_map)}")


if __name__ == "__main__":
    extract_all()
