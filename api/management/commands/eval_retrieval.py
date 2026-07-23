"""
Retrieval quality eval for the RAG pipeline.

Runs a small golden set of (query -> known verse) pairs through the real
retrieve_chunks() against the live, fully-ingested corpus, and reports
Recall@3/@5/@10 and MRR. This is deliberately NOT a pytest test: pytest's
test database only has the handful of fixture verses conftest.py seeds
(see api/tests/conftest.py) -- retrieval quality is only meaningful against
the real ~62k-verse corpus, so this runs as a management command against
whichever database DATABASE_* env vars point at.

Usage:
    python manage.py eval_retrieval
    python manage.py eval_retrieval --verbose
    python manage.py eval_retrieval --translation DBY
"""

from django.core.management.base import BaseCommand

from api.views import retrieve_chunks

# Each entry is a well-known verse and a natural-language query for it.
# `book` must match api_book.name exactly; (chapter, verse) is the specific
# verse the query is about -- a chunk counts as a hit if that verse falls
# anywhere inside the chunk's [start, end] span.
GOLDEN_SET = [
    {'query': 'What is the fruit of the Spirit?', 'book': 'Galatians', 'chapter': 5, 'verse': 22},
    {'query': 'In the beginning God created the heaven and the earth', 'book': 'Genesis', 'chapter': 1, 'verse': 1},
    {'query': 'For God so loved the world that he gave his only begotten Son', 'book': 'John', 'chapter': 3, 'verse': 16},
    {'query': 'The LORD is my shepherd; I shall not want', 'book': 'Psalms', 'chapter': 23, 'verse': 1},
    {'query': 'Blessed are the poor in spirit', 'book': 'Matthew', 'chapter': 5, 'verse': 3},
    {'query': 'Love your enemies and pray for those who persecute you', 'book': 'Matthew', 'chapter': 5, 'verse': 44},
    {'query': 'Let there be light', 'book': 'Genesis', 'chapter': 1, 'verse': 3},
    {'query': 'I am the way, the truth, and the life', 'book': 'John', 'chapter': 14, 'verse': 6},
    {'query': 'Be careful for nothing, but in every thing by prayer', 'book': 'Philippians', 'chapter': 4, 'verse': 6},
    {'query': 'For by grace are ye saved through faith', 'book': 'Ephesians', 'chapter': 2, 'verse': 8},
    {'query': 'For the wages of sin is death', 'book': 'Romans', 'chapter': 6, 'verse': 23},
    {'query': 'Now faith is the substance of things hoped for', 'book': 'Hebrews', 'chapter': 11, 'verse': 1},
    {'query': 'To every thing there is a season, a time to be born, and a time to die', 'book': 'Ecclesiastes', 'chapter': 3, 'verse': 2},
    {'query': 'Honour thy father and thy mother', 'book': 'Exodus', 'chapter': 20, 'verse': 12},
    {'query': 'The fool hath said in his heart, There is no God', 'book': 'Psalms', 'chapter': 14, 'verse': 1},
]

K_VALUES = (3, 5, 10)
MAX_K = max(K_VALUES)


def is_hit(chunk, book, chapter, verse):
    target = (chapter, verse)
    return chunk['book_name'] == book and chunk['start'] <= target <= chunk['end']


class Command(BaseCommand):
    help = 'Evaluate retrieval quality (Recall@k, MRR) against the golden verse set.'

    def add_arguments(self, parser):
        parser.add_argument('--translation', default='KJV', help='KJV or DBY')
        parser.add_argument('--verbose', action='store_true', help='Print every retrieved chunk per query')

    def handle(self, *args, **options):
        translation = options['translation'].upper()
        verbose = options['verbose']

        hits_at_k = {k: 0 for k in K_VALUES}
        reciprocal_ranks = []
        rows = []

        for case in GOLDEN_SET:
            chunks = retrieve_chunks(case['query'], translation, limit=MAX_K)
            rank = next(
                (i for i, c in enumerate(chunks, 1) if is_hit(c, case['book'], case['chapter'], case['verse'])),
                None,
            )
            reciprocal_ranks.append(1 / rank if rank else 0)
            for k in K_VALUES:
                if rank and rank <= k:
                    hits_at_k[k] += 1
            rows.append((case, rank, chunks))

        n = len(GOLDEN_SET)
        self.stdout.write(f"\nRetrieval eval -- {translation}, {n} queries\n" + "=" * 60)
        for case, rank, chunks in rows:
            expected = f"{case['book']} {case['chapter']}:{case['verse']}"
            status = f"hit @{rank}" if rank else "MISS"
            self.stdout.write(f"[{status:>8}] {expected:<20} <- {case['query']!r}")
            if verbose:
                for i, c in enumerate(chunks, 1):
                    marker = '*' if rank == i else ' '
                    self.stdout.write(f"      {marker} {i}. {c['reference']}")

        self.stdout.write("\n" + "-" * 60)
        for k in K_VALUES:
            self.stdout.write(f"Recall@{k}: {hits_at_k[k]}/{n} ({hits_at_k[k] / n:.0%})")
        self.stdout.write(f"MRR:       {sum(reciprocal_ranks) / n:.3f}")
