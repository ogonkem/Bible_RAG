""" 
Fixture definitions for API tests
1. api_client: Provides an instance of APIClient for making requests to the API.
2. auth_client: Provides an authenticated APIClient instance for making requests to the API with a valid user token.
3. seeded_book: Creates and returns a Book instance for testing purposes.
4. seeded_verses: Creates and returns a list of Verse instances associated with the seeded_book for testing purposes.
5. seeded_chunk: Creates and returns a Chunk instance associated with the seeded_book and seeded_verses for testing purposes.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from api.models import Book, Verse, Chunk

User = get_user_model()

@pytest.fixture
def api_client():
    """Provides an instance of APIClient for making requests to the API."""
    return APIClient()

@pytest.fixture
def auth_client(api_client, django_user_model):
    """Provides an authenticated APIClient instance for making requests to the API with a valid user token."""
    user = django_user_model.objects.create_user(username='tester', password='pass1234')
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client

@pytest.fixture
def seeded_book():
    """Creates and returns a Book instance for testing purposes."""
    return Book.objects.create(name='Matthew', testament='NT', chapters=28)

@pytest.fixture
def seeded_verses(seeded_book):
    """Creates and returns a list of Verse instances associated with the seeded_book for testing purposes."""
    verses = []
    texts = [
        "Blessed are the poor in spirit: for theirs is the kingdom of heaven.",
        "Blessed are they that mourn: for they shall be comforted.",
        "Blessed are the meek: for they shall inherit the earth.",
        "Blessed are they which do hunger and thirst after righteousness: for they shall be filled.",
        "Blessed are the merciful: for they shall obtain mercy.",
    ]
    for i, text in enumerate(texts, start=1):
        verses.append(Verse.objects.create(
            book=seeded_book, chapter=5, verse_num=i, text=text, translation='KJV'
        ))
    return verses

@pytest.fixture
def seeded_chunk(seeded_book, seeded_verses):
    """Creates and returns a Chunk instance associated with the seeded_book and seeded_verses for testing purposes."""
    return Chunk.objects.create(
        book=seeded_book,
        start_verse=seeded_verses[0],
        end_verse=seeded_verses[-1],
        combined_text=' '.join(v.text for v in seeded_verses),
        embedding=[0.01] * 384,
        translation='KJV',
    )
