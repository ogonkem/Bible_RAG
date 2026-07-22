#!/usr/bin/env python
"""
Convert Bible CSV files to JSON format - one translation at a time
CORRECT 66 BOOKS: 1-39 OT, 40-66 NT (Song of Solomon = book 22)

CSV format expected: id,b,c,v,t
    id = unique row id (e.g. 1001001)
    b  = book number (e.g. 1 = Genesis)
    c  = chapter number
    v  = verse number
    t  = verse text

Usage:
    python scripts/csv_to_json.py t_kjv.csv
    python scripts/csv_to_json.py t_dby.csv
    python scripts/csv_to_json.py t_kjv.csv --output kjv.json
"""

import csv
import json
import sys
import argparse
from pathlib import Path

data_dir = Path('data/raw')

# CORRECT 66 BOOKS - OT 1-39, NT 40-66
BOOK_NAMES = {
    # Old Testament - 39 books (1-39)
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Samuel", 10: "2 Samuel",
    11: "1 Kings", 12: "2 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "Ezra", 16: "Nehemiah", 17: "Esther", 18: "Job", 19: "Psalms",
    20: "Proverbs", 21: "Ecclesiastes", 22: "Song of Solomon", 23: "Isaiah",
    24: "Jeremiah", 25: "Lamentations", 26: "Ezekiel", 27: "Daniel",
    28: "Hosea", 29: "Joel", 30: "Amos", 31: "Obadiah", 32: "Jonah",
    33: "Micah", 34: "Nahum", 35: "Habakkuk", 36: "Zephaniah", 37: "Haggai",
    38: "Zechariah", 39: "Malachi",

    # New Testament - 27 books (40-66)
    40: "Matthew", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Romans", 46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians",
    52: "1 Thessalonians", 53: "2 Thessalonians", 54: "1 Timothy",
    55: "2 Timothy", 56: "Titus", 57: "Philemon", 58: "Hebrews",
    59: "James", 60: "1 Peter", 61: "2 Peter", 62: "1 John", 63: "2 John",
    64: "3 John", 65: "Jude", 66: "Revelation"
}


def get_book_name(book_identifier):
    """Convert book number to book name"""
    try:
        book_num = int(book_identifier)
        if book_num in BOOK_NAMES:
            return BOOK_NAMES[book_num]
    except (ValueError, TypeError):
        if book_identifier in BOOK_NAMES.values():
            return book_identifier
    return book_identifier


def open_csv_with_fallback(csv_file: Path):
    """Try utf-8 first, fall back to other common encodings for older datasets"""
    encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']

    for encoding in encodings_to_try:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                f.read()  # force full read to confirm it decodes cleanly
            print(f"   (detected encoding: {encoding})")
            return encoding
        except UnicodeDecodeError:
            continue

    # Last resort: latin-1 never raises UnicodeDecodeError (maps byte-for-byte)
    print("   (falling back to latin-1 with replacement for undecodable bytes)")
    return 'latin-1'


def csv_to_json(csv_file: Path, json_file: Path):
    """Convert a single Bible CSV (columns: id,b,c,v,t) to JSON"""
    print(f"Converting {csv_file} -> {json_file}...")

    bible_data = {}
    rows_processed = 0
    rows_skipped = 0

    encoding = open_csv_with_fallback(csv_file)

    with open(csv_file, 'r', encoding=encoding, errors='replace') as f:
        reader = csv.DictReader(f)

        for row in reader:
            book_id = row.get('b', '').strip()
            chapter = row.get('c', '').strip()
            verse = row.get('v', '').strip()
            text = row.get('t', '').strip()

            if not all([book_id, chapter, verse, text]):
                rows_skipped += 1
                continue

            book = get_book_name(book_id)

            if book not in bible_data:
                bible_data[book] = {}
            if chapter not in bible_data[book]:
                bible_data[book][chapter] = {}

            bible_data[book][chapter][verse] = text
            rows_processed += 1

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(bible_data, f, indent=2, ensure_ascii=False)

    total_verses = sum(sum(len(ch) for ch in book.values()) for book in bible_data.values())

    # Separate OT/NT for summary
    ot_books, nt_books = [], []
    for book_name, chapters in bible_data.items():
        count = sum(len(ch) for ch in chapters.values())
        book_num = next((num for num, name in BOOK_NAMES.items() if name == book_name), None)
        if book_num and book_num <= 39:
            ot_books.append((book_num, book_name, count))
        elif book_num and book_num >= 40:
            nt_books.append((book_num, book_name, count))

    ot_books.sort()
    nt_books.sort()

    print(f"\n✅ Conversion Complete: {csv_file.name}")
    print(f"   Rows processed: {rows_processed}")
    print(f"   Rows skipped:   {rows_skipped}")
    print(f"   Total verses:   {total_verses}")
    print(f"   OT books found: {len(ot_books)} (expected 39)")
    print(f"   NT books found: {len(nt_books)} (expected 27)")
    print(f"   TOTAL books:    {len(ot_books) + len(nt_books)} (expected 66)")
    print(f"   Saved to:       {json_file}")

    missing = 66 - (len(ot_books) + len(nt_books))
    if missing:
        print(f"   ⚠️  {missing} book(s) missing — check book numbering in the CSV")


def main():
    parser = argparse.ArgumentParser(description="Convert one Bible CSV file to JSON")
    parser.add_argument('csv_filename', help="CSV filename inside data/raw/ (e.g. t_kjv.csv)")
    parser.add_argument('--output', '-o', help="Output JSON filename (default: derived from input)")
    args = parser.parse_args()

    csv_path = data_dir / args.csv_filename

    if not csv_path.exists():
        print(f"❌ {csv_path} not found")
        print(f"\nFiles available in {data_dir}:")
        for f in sorted(data_dir.glob('*.csv')):
            print(f"   - {f.name}")
        sys.exit(1)

    # Derive output name: t_kjv.csv -> kjv.json, t_dby.csv -> dby.json
    if args.output:
        json_path = data_dir / args.output
    else:
        stem = csv_path.stem  # e.g. "t_kjv"
        translation = stem[2:] if stem.startswith('t_') else stem  # -> "kjv"
        json_path = data_dir / f"{translation}.json"

    csv_to_json(csv_path, json_path)


if __name__ == '__main__':
    main()