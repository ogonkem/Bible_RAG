import json
import pytest

pytestmark = pytest.mark.django_db

def test_chat_sessions_rejects_anonymous(api_client):
    resp = api_client.get('/api/chat-sessions/')
    assert resp.status_code == 401

def test_chat_sessions_allows_authenticated(auth_client):
    resp = auth_client.get('/api/chat-sessions/')
    assert resp.status_code == 200

def test_chat_sessions_create_requires_auth(auth_client):
    resp = auth_client.post(
        '/api/chat-sessions/',
        data=json.dumps({'session_id': 'sess-1', 'title': 'Test Session'}),
        content_type='application/json',
    )
    assert resp.status_code == 201
