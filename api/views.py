import json

from django.db import connection

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


def retrieve_chunks(query, translation_filter='all', limit=10):
    """
    Shared retrieval logic used by both /search/ (retrieval only)
    and /ask/ (retrieval + LLM synthesis).
    """
    query_vector = embedding_model.encode(query).tolist()
    query_vector_str = str(query_vector)  # pgvector literal format: "[0.1,0.2,...]"

    sql = """
        SELECT id, combined_text, start_verse_id, end_verse_id, translation
        FROM api_chunk
        {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    params = [query_vector_str]
    where = ""
    if translation_filter.upper() in ('KJV', 'DBY'):
        where = "WHERE translation = %s"
        params = [translation_filter.upper(), query_vector_str]
    params.append(limit)

    with connection.cursor() as cursor:
        cursor.execute(sql.format(where=where), params)
        rows = cursor.fetchall()

    return [
        {
            'id': chunk_id,
            'text': text,
            'start_verse_id': start,
            'end_verse_id': end,
            'translation': translation,
        }
        for chunk_id, text, start, end, translation in rows
    ]


def build_prompt(query, chunks):
    """Format retrieved chunks + question into a prompt for the LLM."""
    verses_block = "\n\n".join(
        f"[{c['translation']}] {c['text']}" for c in chunks
    )
    return f"""{SYSTEM_PROMPT}

RELEVANT SCRIPTURE:
{verses_block}

QUESTION: {query}

ANSWER:"""


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
            'reference': f"Ref {c['start_verse_id']}-{c['end_verse_id']}",
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
    Retrieval + LLM synthesis — the actual RAG call. Slower (~5-30s).
    Returns an AI-generated answer grounded in the retrieved verses.
    Use this for the AI response beneath the verse cards in the UI.
    """
    data = json.loads(request.body)
    query = data.get('query', '')
    translation_filter = data.get('translation_filter', 'all')

    if not query:
        return Response({'error': 'Query required.'}, status=400)

    chunks = retrieve_chunks(query, translation_filter, limit=5)

    if not chunks:
        return Response({
            'answer': "I couldn't find any relevant passages for that question.",
            'verses': [],
        })

    prompt = build_prompt(query, chunks)

    try:
        llm = get_llm_provider()
        answer = llm.generate(prompt)
    except ValueError as e:
        # Missing/invalid provider config (e.g. no API key set)
        return Response({'error': f'LLM configuration error: {e}'}, status=503)
    except Exception as e:
        # Network/timeout/API errors from whichever provider is active
        return Response({'error': f'LLM service unavailable: {e}'}, status=503)

    return Response({
        'answer': answer,
        'verses': [
            {'translation': c['translation'], 'text': c['text'][:200]}
            for c in chunks
        ],
    })


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
