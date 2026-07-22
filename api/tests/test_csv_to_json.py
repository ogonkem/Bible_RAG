"""
Unit tests for the csv_to_json script.
1. test_all_66_books_mapped: Ensures that all 66 books of the Bible are present in the BOOK_NAMES mapping.
2. test_song_of_solomon_is_book_22: Validates that "Song of Solomon" is correctly mapped as the 22nd book in the BOOK_NAMES list.
3. test_ot_nt_boundary: Checks the boundary between the Old Testament and New Testament in the BOOK_NAMES list.
4. test_get_book_name_by_number: Parameterized test to verify that get_book_name returns the correct book name for given book numbers.
5. test_get_book_name_passthrough_for_already_named: Ensures that get_book_name returns the same name if the input is already a book name.  
"""
import pytest
from scripts.csv_to_json import get_book_name, BOOK_NAMES

def test_all_66_books_mapped():
    """Ensures that all 66 books of the Bible are present in the BOOK_NAMES mapping."""
    assert len(BOOK_NAMES) == 66

def test_song_of_solomon_is_book_22():
    """Validates that "Song of Solomon" is correctly mapped as the 22nd book in the BOOK_NAMES list."""
    assert BOOK_NAMES[22] == "Song of Solomon"

def test_ot_nt_boundary():
    """Checks the boundary between the Old Testament and New Testament in the BOOK_NAMES list."""
    assert BOOK_NAMES[39] == "Malachi"     # last OT book
    assert BOOK_NAMES[40] == "Matthew"     # first NT book

@pytest.mark.parametrize("book_id,expected", [
    ("1", "Genesis"), ("39", "Malachi"), ("40", "Matthew"), ("66", "Revelation"),
])
def test_get_book_name_by_number(book_id, expected):
    """Parameterized test to verify that get_book_name returns the correct book name for given book numbers."""
    assert get_book_name(book_id) == expected

def test_get_book_name_passthrough_for_already_named():
    """Ensures that get_book_name returns the same name if the input is already a book name."""
    assert get_book_name("Genesis") == "Genesis"
