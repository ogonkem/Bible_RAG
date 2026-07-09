#!/usr/bin/env python
"""
Convert Bible CSV files to JSON format
CORRECT 66 BOOKS: 1-39 OT, 40-66 NT
Includes Song of Solomon as book 22
"""

import csv
import json
from pathlib import Path

data_dir = Path('data/raw')

# CORRECT 66 BOOKS - OT 1-39, NT 40-66
BOOK_NAMES = {
    # Old Testament - 39 books (1-39)
    1: "Genesis",
    2: "Exodus",
    3: "Leviticus",
    4: "Numbers",
    5: "Deuteronomy",
    6: "Joshua",
    7: "Judges",
    8: "Ruth",
    9: "1 Samuel",
    10: "2 Samuel",
    11: "1 Kings",
    12: "2 Kings",
    13: "1 Chronicles",
    14: "2 Chronicles",
    15: "Ezra",
    16: "Nehemiah",
    17: "Esther",
    18: "Job",
    19: "Psalms",
    20: "Proverbs",
    21: "Ecclesiastes",
    22: "Song of Solomon",  # ← ADDED
    23: "Isaiah",
    24: "Jeremiah",
    25: "Lamentations",
    26: "Ezekiel",
    27: "Daniel",
    28: "Hosea",
    29: "Joel",
    30: "Amos",
    31: "Obadiah",
    32: "Jonah",
    33: "Micah",
    34: "Nahum",
    35: "Habakkuk",
    36: "Zephaniah",
    37: "Haggai",
    38: "Zechariah",
    39: "Malachi",
    
    # New Testament - 27 books (40-66)
    40: "Matthew",
    41: "Mark",
    42: "Luke",
    43: "John",
    44: "Acts",
    45: "Romans",
    46: "1 Corinthians",
    47: "2 Corinthians",
    48: "Galatians",
    49: "Ephesians",
    50: "Philippians",
    51: "Colossians",
    52: "1 Thessalonians",
    53: "2 Thessalonians",
    54: "1 Timothy",
    55: "2 Timothy",
    56: "Titus",
    57: "Philemon",
    58: "Hebrews",
    59: "James",
    60: "1 Peter",
    61: "2 Peter",
    62: "1 John",
    63: "2 John",
    64: "3 John",
    65: "Jude",
    66: "Revelation"
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

def csv_to_json(csv_file, json_file):
    """Convert Bible CSV to JSON"""
    print(f"Converting {csv_file} to JSON...")
    
    bible_data = {}
    rows_processed = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            book_id = row.get('book', '').strip()
            chapter = row.get('chapter', '').strip()
            verse = row.get('verse', '').strip()
            text = row.get('text', '').strip()
            
            if not all([book_id, chapter, verse, text]):
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
    
    # Separate OT/NT
    ot_books = []
    nt_books = []
    
    for book_name, chapters in bible_data.items():
        count = sum(len(ch) for ch in chapters.values())
        
        book_num = None
        for num, name in BOOK_NAMES.items():
            if name == book_name:
                book_num = num
                break
        
        if book_num and book_num <= 39:
            ot_books.append((book_num, book_name, count))
        elif book_num and book_num >= 40:
            nt_books.append((book_num, book_name, count))
    
    ot_books.sort()
    nt_books.sort()
    
    print(f"\n✅ Conversion Complete:")
    print(f"   Rows processed: {rows_processed}")
    print(f"   Total verses: {total_verses}")
    print(f"\nOld Testament ({len(ot_books)} books - 1-39):")
    for num, name, count in ot_books:
        print(f"   {num:2d}. {name:20s} - {count:5d} verses")
    
    print(f"\nNew Testament ({len(nt_books)} books - 40-66):")
    for num, name, count in nt_books:
        print(f"   {num:2d}. {name:20s} - {count:5d} verses")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(ot_books)} OT (1-39) + {len(nt_books)} NT (40-66) = {len(ot_books) + len(nt_books)} BOOKS")
    print(f"{'='*60}")

# Convert
kjv_csv = data_dir / 't_kjv.csv'
kjv_json = data_dir / 'kjv.json'

if kjv_csv.exists():
    csv_to_json(kjv_csv, kjv_json)
    print("\n✅ CSV to JSON conversion complete!")
    print("\nNext steps:")
    print("1. docker-compose exec web python manage.py ingest_bible --source kjv")
    print("2. docker-compose exec web python manage.py chunk_and_embed")
else:
    print(f"❌ {kjv_csv} not found")
    exit(1)
