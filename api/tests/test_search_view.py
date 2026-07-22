"""
Unit tests for the search view in the api app.
1. test_search_requires_query: Ensures that the search endpoint returns a 400 error when no query is provided in the request body.
2. test_search_no_auth_required: Validates that the search endpoint can be accessed without authentication and returns a successful response with verses.
3. test_search_translation_filter_kjv_only: Checks that when the translation filter is set to 'KJV', only verses from the KJV translation are returned in the search results.
"""
import json
import pytest
from unittest.mock import patch
import numpy as np

pytestmark = pytest.mark.django_db

@patch('api.views.embedding_model')
def test_search_requires_query(mock_model, api_client):
    """Ensures that the search endpoint returns a 400 error when no query is provided in the request body."""
    resp = api_client.post('/api/search/', data=json.dumps({}), content_type='application/json')
    assert resp.status_code == 400

@patch('api.views.embedding_model')
def test_search_no_auth_required(mock_model, api_client, seeded_chunk):
    """Validates that the search endpoint can be accessed without authentication and returns a successful response with verses."""
    mock_model.encode.return_value = np.array([0.01] * 384)
    resp = api_client.post(
        '/api/search/',
        data=json.dumps({'query': 'blessed are the poor', 'translation_filter': 'all'}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert 'verses' in resp.json()

@patch('api.views.embedding_model')
def test_search_translation_filter_kjv_only(mock_model, api_client, seeded_chunk):
    """Checks that when the translation filter is set to 'KJV', only verses from the KJV translation are returned in the search results."""
    mock_model.encode.return_value = np.array([0.01] * 384)
    resp = api_client.post(
        '/api/search/',
        data=json.dumps({'query': 'blessed', 'translation_filter': 'KJV'}),
        content_type='application/json',
    )
    body = resp.json()
    assert all(v['translation'] == 'KJV' for v in body['verses'])
