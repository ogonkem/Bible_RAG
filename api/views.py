import json

from django.db import connection
from django.http import StreamingHttpResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sentence_transformers import SentenceTransformer

from api.models import ChatSession, ChatMessage
from api.llm_providers import get_llm_provider


# ============================================================
# Shared setup
# ============================================================

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

SYSTEM_PROMPT = """You are a knowledgeable Bible commentator.
Use ONLY the provided scripture passages to answer the question.
Cite specific verses. Acknowledge if a topic is not covered in the provided passages.
Do not add doctrine beyond what the text supports."""


def format_reference(book_name, start_chapter, start_verse, end_chapter, end_verse):
    """Turn a chunk's book/chapter/verse span into a human-readable reference."""
    if start_chapter == end_chapter:
        if start_verse == end_verse:
            return f"{book_name} {start_chapter}:{start_verse}"
        return f"{book_name} {start_chapter}:{start_verse}-{end_verse}"
    return f"{book_name} {start_chapter}:{start_verse}-{end_chapter}:{end_verse}"


def retrieve_chunks(query, translation_filter='all', limit=10):
    """
    Shared retrieval logic used by both /search/ (retrieval only)
    and /ask/ (retrieval + LLM synthesis).
    """
    query_vector = embedding_model.encode(query).tolist()
    query_vector_str = str(query_vector)  # pgvector literal format: "[0.1,0.2,...]"

    sql = """
        SELECT
            c.id, c.combined_text, c.translation,
            b.name AS book_name,
            sv.chapter AS start_chapter, sv.verse_num AS start_verse_num,
            ev.chapter AS end_chapter, ev.verse_num AS end_verse_num
        FROM api_chunk c
        JOIN api_book b ON b.id = c.book_id
        JOIN api_verse sv ON sv.id = c.start_verse_id
        JOIN api_verse ev ON ev.id = c.end_verse_id
        {where}
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    params = [query_vector_str]
    where = ""
    if translation_filter.upper() in ('KJV', 'DBY'):
        where = "WHERE c.translation = %s"
        params = [translation_filter.upper(), query_vector_str]
    params.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(sql.format(where=where), params)
        rows = cursor.fetchall()

    return [
        {
            'id': chunk_id,
            'text': text,
            'translation': translation,
            'reference': format_reference(book_name, start_chapter, start_verse_num, end_chapter, end_verse_num),
            # Structured span, for callers (e.g. the retrieval eval) that need
            # to check whether a specific verse falls inside this chunk
            # without re-parsing the human-readable reference string.
            'book_name': book_name,
            'start': (start_chapter, start_verse_num),
            'end': (end_chapter, end_verse_num),
        }
        for (
            chunk_id, text, translation, book_name,
            start_chapter, start_verse_num, end_chapter, end_verse_num,
        ) in rows
    ]


def build_prompt(query, chunks):
    """Format retrieved chunks + question into a prompt for the LLM."""
    verses_block = "\n\n".join(
        f"[{c['translation']} — {c['reference']}] {c['text']}" for c in chunks
    )
    return f"""{SYSTEM_PROMPT}

RELEVANT SCRIPTURE:
{verses_block}

QUESTION: {query}

ANSWER:"""


def _sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _get_or_create_session(session_id, title):
    if not session_id:
        return None
    session, _ = ChatSession.objects.get_or_create(
        session_id=session_id,
        defaults={'title': title},
    )
    return session


# ============================================================
# Public endpoints — no authentication required
# ============================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def search(request):
    """
    Retrieval only. Fast (~50-100ms). Returns raw verse chunks, no LLM call.
    Use this for instant verse cards in the UI.
    """
    data = json.loads(request.body)
    query = data.get('query', '')
    translation_filter = data.get('translation_filter', 'all')

    if not query:
        return Response({'error': 'Query required.'}, status=400)

    chunks = retrieve_chunks(query, translation_filter, limit=10)

    verses = [
        {
            'reference': c['reference'],
            'translation': c['translation'],
            'text': c['text'][:200],
        }
        for c in chunks
    ]

    return Response({'verses': verses, 'total': len(verses)})


@api_view(['POST'])
@permission_classes([AllowAny])
def ask(request):
    """
    Retrieval + LLM synthesis — the actual RAG call.

    Streams the answer back as Server-Sent Events by default (much better
    perceived latency than waiting ~50s for a single response on CPU-bound
    local models). Pass `"stream": false` in the request body to get a
    single JSON response instead, e.g. for scripts/tests.

    Pass `"session_id"` to persist the turn to ChatSession/ChatMessage so
    it shows up in /chat-history/<session_id>/.
    """
    data = json.loads(request.body)
    query = data.get('query', '')
    translation_filter = data.get('translation_filter', 'all')
    session_id = data.get('session_id')
    stream = data.get('stream', True)

    if not query:
        return Response({'error': 'Query required.'}, status=400)

    chunks = retrieve_chunks(query, translation_filter, limit=5)
    session = _get_or_create_session(session_id, query[:200] or 'Bible Discussion')

    if not chunks:
        answer = "I couldn't find any relevant passages for that question."
        if session:
            ChatMessage.objects.create(session=session, role='user', content=query, retrieved_verses=[])
            ChatMessage.objects.create(session=session, role='assistant', content=answer, retrieved_verses=[])
        return Response({'answer': answer, 'verses': []})

    prompt = build_prompt(query, chunks)
    verses_payload = [
        {'reference': c['reference'], 'translation': c['translation'], 'text': c['text'][:200]}
        for c in chunks
    ]

    if session:
        ChatMessage.objects.create(session=session, role='user', content=query, retrieved_verses=[])

    if not stream:
        try:
            llm = get_llm_provider()
            answer = llm.generate(prompt)
        except ValueError as e:
            # Missing/invalid provider config (e.g. no API key set)
            return Response({'error': f'LLM configuration error: {e}'}, status=503)
        except Exception as e:
            # Network/timeout/API errors from whichever provider is active
            return Response({'error': f'LLM service unavailable: {e}'}, status=503)

        if session:
            ChatMessage.objects.create(session=session, role='assistant', content=answer, retrieved_verses=verses_payload)

        return Response({'answer': answer, 'verses': verses_payload})

    def event_stream():
        yield _sse_event('verses', {'verses': verses_payload})
        answer_parts = []
        try:
            llm = get_llm_provider()
            for token in llm.generate_stream(prompt):
                answer_parts.append(token)
                yield _sse_event('token', {'text': token})
        except ValueError as e:
            yield _sse_event('error', {'error': f'LLM configuration error: {e}'})
            return
        except Exception as e:
            yield _sse_event('error', {'error': f'LLM service unavailable: {e}'})
            return

        answer = ''.join(answer_parts).strip()
        if session:
            ChatMessage.objects.create(session=session, role='assistant', content=answer, retrieved_verses=verses_payload)
        yield _sse_event('done', {'answer': answer})

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # disable proxy buffering (e.g. nginx) so tokens flush immediately
    return response


# ============================================================
# Protected endpoints — token authentication required
# ============================================================

class ChatSessionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = ChatSession.objects.all().values(
            'session_id', 'title', 'created_at', 'updated_at'
        )
        return Response({'sessions': list(sessions)})

    def post(self, request):
        data = json.loads(request.body)
        session, _ = ChatSession.objects.get_or_create(
            session_id=data['session_id'],
            defaults={'title': data.get('title', 'Bible Discussion')}
        )
        return Response({'session_id': session.session_id, 'title': session.title}, status=201)


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        messages = session.messages.values('role', 'content', 'retrieved_verses', 'created_at')
        return Response({'messages': list(messages)})
