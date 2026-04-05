#!/usr/bin/env python3
"""
Post-process pdftotext output into readable Markdown.
Usage: python3 format.py wang-xing | zhang-yi-ming
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def collapse_cjk_spaces(text: str) -> str:
    """Remove spaces between consecutive CJK characters (PDF justification artifact)."""
    cjk = r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\uff00-\uffef\u3000-\u303f]'
    pat = re.compile(r'(' + cjk + r') (' + cjk + r')')
    prev = None
    while prev != text:
        prev = text
        text = pat.sub(r'\1\2', text)
    return text


SENTENCE_END = re.compile(r'[。！？…」』》】；\.\!\?]["」』》】]?$')

def join_wrapped_lines(lines: list[str]) -> list[str]:
    """
    Merge lines that were soft-wrapped by the PDF renderer.
    A line is joined to the next if it does NOT end with sentence-ending punctuation
    and the next line is non-empty.
    """
    out: list[str] = []
    buf = ''
    for line in lines:
        if not line.strip():
            if buf:
                out.append(buf)
                buf = ''
            out.append('')
        elif buf and not SENTENCE_END.search(buf):
            buf = buf + line.strip()
        else:
            if buf:
                out.append(buf)
            buf = line.strip()
    if buf:
        out.append(buf)
    return out


# ---------------------------------------------------------------------------
# Wang Xing formatter
# ---------------------------------------------------------------------------

PAGE_HEADER = re.compile(r'^第\s*\d+\s*页\s*/\s*共\s*\d+\s*页\s*$')
SITE_HEADER = re.compile(r'^www\.hackersay\.com\s*$')
ENTRY_NUM   = re.compile(r'^(\d+)\.\s*$')
TIMESTAMP   = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})(.*?)$')


UI_ARTIFACT  = re.compile(r'^(取消收藏\s*转发|收藏\s*转发|举报)\s*$')


def format_wang_xing(raw: str) -> str:
    lines = raw.splitlines()

    # --- Pass 1: strip page headers, site banners, and UI button artifacts ---
    cleaned: list[str] = []
    for line in lines:
        if PAGE_HEADER.match(line) or SITE_HEADER.match(line) or UI_ARTIFACT.match(line):
            continue
        cleaned.append(line)

    # --- Pass 2: collect entries ---
    # Each entry: { num, content_lines, timestamp }
    intro_lines: list[str] = []
    entries: list[dict] = []
    current: dict | None = None

    for line in cleaned:
        m_num = ENTRY_NUM.match(line)
        m_ts  = TIMESTAMP.match(line)

        if m_num:
            if current is not None:
                entries.append(current)
            current = {'num': int(m_num.group(1)), 'content': [], 'ts': ''}
        elif m_ts and current is not None:
            # Append timestamp; also capture suffix like '转自xxx'
            ts_date = m_ts.group(1)
            ts_suffix = m_ts.group(2).strip()
            ts_suffix = re.sub(r'^通过\s*', '', ts_suffix)
            if ts_suffix:
                current['ts'] = f"{ts_date} · {ts_suffix}"
            else:
                current['ts'] = ts_date
        elif current is None:
            intro_lines.append(line)
        else:
            current['content'].append(line)

    if current is not None:
        entries.append(current)

    # --- Pass 3: join wrapped content lines ---
    for e in entries:
        joined = join_wrapped_lines(e['content'])
        # Collapse blank lines at start/end
        while joined and joined[0] == '':
            joined.pop(0)
        while joined and joined[-1] == '':
            joined.pop()
        e['content'] = joined

    # --- Pass 4: render Markdown ---
    out: list[str] = []

    # Intro block (title, source, boilerplate)
    out.append('## 简介\n\n')
    for line in intro_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('http'):
            out.append(f'[{stripped}]({stripped})\n\n')
        else:
            out.append(stripped + '\n\n')
    out.append('---\n\n')

    # Load image map if available
    img_map: dict = {}
    map_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "wang-xing", "images", "map.json")
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as f:
            img_map = json.load(f)

    for e in entries:
        num  = e['num']
        body = '\n\n'.join(e['content']) if e['content'] else ''
        ts   = e['ts']
        imgs = img_map.get(str(num), [])

        out.append(f'### {num}\n\n')
        if body:
            out.append(body + '\n')
        for fname in imgs:
            out.append(f'\n![图片](images/{fname})\n')
        if not body and not imgs:
            out.append('（无内容）\n')
        if ts:
            out.append(f'\n*{ts}*\n')
        out.append('\n---\n\n')

    return ''.join(out)


# ---------------------------------------------------------------------------
# Zhang Yiming formatter
# ---------------------------------------------------------------------------

SECTION_HDR    = re.compile(r'^(\d{2})\s+(关于\S+|论\S+|谈\S+|\S{2,6})')
ZY_ENTRY_START = re.compile(r'^\s*(\d{1,3})\.\s*(.*)')


def split_section_fused_entry(line: str):
    """
    '01 关于成长001.内容...' → ('01 关于成长', '001', '内容...')
    Returns (section_title, entry_num_str, entry_content) or None if not matching.
    """
    m = re.match(r'^(\d{2}\s+\S+?)(\d{3})\.(.*)', line)
    if m:
        return m.group(1).strip(), m.group(2), m.group(3).strip()
    return None


def format_zhang_yiming(raw: str) -> str:
    lines = raw.splitlines()

    # --- Pass 1: collapse CJK spaces, strip leading whitespace ---
    cleaned: list[str] = []
    for line in lines:
        line = re.sub(r'^\s+', '', line)          # strip leading indent
        line = collapse_cjk_spaces(line)
        cleaned.append(line)

    # --- Pass 2: parse sections and entries ---
    # Structure: optional intro, then sections containing entries
    intro_lines: list[str] = []
    sections: list[dict] = []     # {title, entries: [{num, lines}]}
    cur_section: dict | None = None
    cur_entry: dict | None = None

    def flush_entry():
        nonlocal cur_entry
        if cur_entry and cur_section is not None:
            cur_section['entries'].append(cur_entry)
        cur_entry = None

    def flush_section():
        nonlocal cur_section
        flush_entry()
        if cur_section is not None:
            sections.append(cur_section)
        cur_section = None

    for line in cleaned:
        # Try to split fused section+entry header (e.g. '01 关于成长001.内容')
        fused = split_section_fused_entry(line)
        if fused:
            flush_section()
            sec_title, entry_num, entry_content = fused
            cur_section = {'title': sec_title, 'entries': []}
            cur_entry = {'num': entry_num, 'lines': [entry_content] if entry_content else []}
            continue

        # Plain section header with no fused entry
        m_sec = SECTION_HDR.match(line)
        if m_sec and cur_entry is None:
            flush_section()
            cur_section = {'title': line.strip(), 'entries': []}
            continue

        # Entry start
        m_entry = ZY_ENTRY_START.match(line)
        if m_entry and cur_section is not None:
            flush_entry()
            num_str  = m_entry.group(1).zfill(3)
            rest     = m_entry.group(2).strip()
            cur_entry = {'num': num_str, 'lines': [rest] if rest else []}
            continue

        # Content / intro
        if cur_entry is not None:
            cur_entry['lines'].append(line)
        elif cur_section is not None:
            pass  # ignore inter-entry blanks at section level
        else:
            intro_lines.append(line)

    flush_section()

    # --- Pass 3: join wrapped lines within each entry ---
    for sec in sections:
        for entry in sec['entries']:
            joined = join_wrapped_lines(entry['lines'])
            while joined and joined[0] == '':
                joined.pop(0)
            while joined and joined[-1] == '':
                joined.pop()
            entry['lines'] = joined

    # --- Pass 4: render Markdown ---
    out: list[str] = []

    # Intro: preserve each line as a paragraph (no aggressive joining)
    if intro_lines:
        out.append('## 编者前言\n\n')
        para: list[str] = []
        for line in intro_lines:
            if not line.strip():
                if para:
                    out.append(''.join(para) + '\n\n')
                    para = []
            else:
                # Only join if previous line clearly doesn't end the sentence
                # Short lines (titles/bylines) are never merged forward
                if para and not SENTENCE_END.search(para[-1]) and len(para[-1]) > 25:
                    para[-1] = para[-1] + line.strip()
                else:
                    if para:
                        out.append(''.join(para) + '\n\n')
                    para = [line.strip()]
        if para:
            out.append(''.join(para) + '\n\n')
        out.append('---\n\n')

    for sec in sections:
        out.append(f'## {sec["title"]}\n\n')
        for entry in sec['entries']:
            body = '\n\n'.join(entry['lines']) if entry['lines'] else '（无内容）'
            out.append(f'### {entry["num"]}\n\n')
            out.append(body + '\n\n')
            out.append('---\n\n')

    return ''.join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: format.py <wang-xing|zhang-yi-ming>", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]
    raw = sys.stdin.read()

    if key == 'wang-xing':
        print(format_wang_xing(raw))
    elif key == 'zhang-yi-ming':
        print(format_zhang_yiming(raw))
    else:
        print(f"Unknown key: {key}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
