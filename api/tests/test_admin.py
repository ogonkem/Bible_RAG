import pytest
from django.contrib import admin
from api.models import Book, Verse, Chunk, ChatSession, ChatMessage

@pytest.mark.parametrize("model", [Book, Verse, Chunk, ChatSession, ChatMessage])
def test_model_registered_in_admin(model):
    assert model in admin.site._registry
