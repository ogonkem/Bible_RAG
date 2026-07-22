"""
Unit tests for the URL routing in the api app.
1. test_search_url_resolves: Validates that the 'search' URL name correctly resolves to the expected path.
2. test_chat_sessions_url_resolves: Validates that the 'chat-sessions' URL name correctly resolves to the expected path.
3. test_chat_history_url_resolves: Validates that the 'chat-history' URL name correctly resolves to the expected path with a given session ID.
"""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_search_url_resolves():
    """Validates that the 'search' URL name correctly resolves to the expected path."""
    assert reverse('search') == '/api/search/'

def test_chat_sessions_url_resolves():
    """Validates that the 'chat-sessions' URL name correctly resolves to the expected path."""
    assert reverse('chat-sessions') == '/api/chat-sessions/'

def test_chat_history_url_resolves():
    """Validates that the 'chat-history' URL name correctly resolves to the expected path with a given session ID."""
    assert reverse('chat-history', args=['abc123']) == '/api/chat-history/abc123/'
