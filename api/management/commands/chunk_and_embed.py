import torch
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from api.models import Book, Verse, Chunk

class Command(BaseCommand):
    help = 'Create overlapping chunks and generate embeddings for one translation'

    def add_arguments(self, parser):
        parser.add_argument('--translation', required=True, help='KJV or DBY')
        parser.add_argument('--chunk_size', type=int, default=5)
        parser.add_argument('--overlap', type=int, default=2)
        parser.add_argument('--gpu', action='store_true')

    def handle(self, *args, **options):
        translation = options['translation'].upper()
        chunk_size = options['chunk_size']
        overlap = options['overlap']
        step_size = chunk_size - overlap
        use_gpu = options['gpu'] and torch.cuda.is_available()

        self.stdout.write(f"Chunking {translation} using {'GPU' if use_gpu else 'CPU'}")

        model = SentenceTransformer('all-MiniLM-L6-v2')
        if use_gpu:
            model = model.cuda()

        for book in Book.objects.all():
            verses = list(Verse.objects.filter(book=book, translation=translation)
                          .order_by('chapter', 'verse_num'))
            windows = [
                verses[i:i + chunk_size]
                for i in range(0, len(verses), step_size)
                if i + chunk_size <= len(verses)
            ]
            if not windows:
                continue

            # Batch-encode per book instead of one text at a time -- ~2x
            # faster on CPU, and encode() returns numpy arrays regardless
            # of device, so no separate GPU/CPU handling is needed here.
            texts = [' '.join(v.text for v in window) for window in windows]
            embeddings = model.encode(texts, batch_size=64, show_progress_bar=False)

            chunks_to_create = [
                Chunk(
                    book=window[0].book,
                    start_verse=window[0],
                    end_verse=window[-1],
                    combined_text=text,
                    embedding=embedding,
                    translation=translation,
                )
                for window, text, embedding in zip(windows, texts, embeddings)
            ]
            Chunk.objects.bulk_create(chunks_to_create, batch_size=100, ignore_conflicts=True)
            self.stdout.write(f"  {book.name}: {len(chunks_to_create)} chunks")

        self.stdout.write(self.style.SUCCESS(f"{translation} chunking complete!"))
