"""
Unit tests for the models in the api app.
1. test_verse_uniqueness_constraint: Ensures that the uniqueness constraint on the Verse model is enforced, preventing duplicate verses for the same book, chapter, verse number, and translation.  
2. test_same_verse_different_translation_is_allowed: Validates that the same verse can exist in different translations without violating the uniqueness constraint.
3. test_chunk_str_representation: Checks that the string representation of a Chunk instance includes the book name, providing a meaningful description of the chunk.
4. test_embedding_dimension: Confirms that the embedding field of a Chunk instance has the expected dimension (384), ensuring that embeddings are correctly generated and stored.
"""

import pytest
from django.db import IntegrityError
from api.models import Book, Verse, Chunk

pytestmark = pytest.mark.django_db

def test_verse_uniqueness_constraint(seeded_book):
    """Ensures that the uniqueness constraint on the Verse model is enforced, preventing duplicate verses for the same book, chapter, verse number, and translation."""
    Verse.objects.create(book=seeded_book, chapter=1, verse_num=1, text="a", translation='KJV')
    with pytest.raises(IntegrityError):
        Verse.objects.create(book=seeded_book, chapter=1, verse_num=1, text="b", translation='KJV')

def test_same_verse_different_translation_is_allowed(seeded_book):
    """Validates that the same verse can exist in different translations without violating the uniqueness constraint."""
    Verse.objects.create(book=seeded_book, chapter=1, verse_num=1, text="a", translation='KJV')
    # should NOT raise -- different translation is a distinct row
    Verse.objects.create(book=seeded_book, chapter=1, verse_num=1, text="b", translation='DBY')
    assert Verse.objects.count() == 2

def test_chunk_str_representation(seeded_chunk):
    """Checks that the string representation of a Chunk instance includes the book name, providing a meaningful description of the chunk."""
    assert 'Matthew' in str(seeded_chunk)

def test_embedding_dimension(seeded_chunk):
    """Confirms that the embedding field of a Chunk instance has the expected dimension (384), ensuring that embeddings are correctly generated and stored."""
    assert len(seeded_chunk.embedding) == 384
