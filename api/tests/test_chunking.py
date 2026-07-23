import pytest
"""
Unit tests for the chunking logic.
1. make_windows: Tests the make_windows function to ensure it correctly creates overlapping windows of verses
2. test_chunk_count_for_known_verse_list: Validates that the correct number of windows are created for a known list of verses with specified chunk size and overlap.
3. test_no_windows_when_fewer_verses_than_chunk_size: Ensures that no windows are created when the number of verses is less than the specified chunk size.
"""

def make_windows(items, chunk_size, overlap):
    """Creates overlapping windows of items based on the specified chunk size and overlap."""
    step = chunk_size - overlap
    windows = []
    for i in range(0, len(items), step):
        if i + chunk_size <= len(items):
            windows.append(items[i:i + chunk_size])
    return windows

def test_chunk_count_for_known_verse_list():
    """Validates that the correct number of windows are created for a known list of verses with specified chunk size and overlap."""
    verses = list(range(1, 11))  # 10 verses
    windows = make_windows(verses, chunk_size=5, overlap=2)
    # step = chunk_size - overlap = 3, so windows start at i=0,3,6,9.
    # The i+chunk_size<=len(items) guard drops any window that would run
    # past the end rather than shortening it, so i=6 (would need items
    # 7-11) and i=9 are excluded -- verses 9 and 10 end up in no window.
    assert len(windows) == 2
    assert windows[0] == [1, 2, 3, 4, 5]
    assert windows[1] == [4, 5, 6, 7, 8]   # verses 4-5 overlap with window 0

def test_no_windows_when_fewer_verses_than_chunk_size():
    """Ensures that no windows are created when the number of verses is less than the specified chunk size."""
    verses = list(range(1, 4))  # only 3 verses
    windows = make_windows(verses, chunk_size=5, overlap=2)
    assert windows == []
