from django.db import models
from pgvector.django import VectorField, HnswIndex

# Create your models here.
class Book(models.Model):
    TESTAMENT_CHOICES = [
        ('OT', 'Old Testament'),
        ('NT', 'New Testament'),
    ]
    name = models.CharField(max_length=100, unique=True)
    testament = models.CharField(max_length=2, choices=TESTAMENT_CHOICES)
    chapters = models.IntegerField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Verse(models.Model):
    TRANSLATION_CHOICES = [
        ('KJV', 'King James Version'),
        ('DBY', 'Darby')
    ]
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='verses')
    chapter = models.IntegerField()
    verse_num = models.IntegerField()
    text = models.TextField()
    translation = models.CharField(max_length=3, choices=TRANSLATION_CHOICES, default='KJV')

    class Meta:
        unique_together = ('book', 'chapter', 'verse_num', 'translation')
        indexes = [
            models.Index(fields=['translation', 'book', 'chapter'])
        ]

    def __str__(self):
        return f"{self.book.name} {self.chapter}:{self.verse_num} ({self.translation})"
    

class Chunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    start_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name='chunk_start')
    end_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name='chunk_end')
    combined_text = models.TextField()
    embedding = VectorField(dimensions=384)
    translation = models.CharField(max_length=3, default='KJV')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A given verse span + translation always produces the same chunk,
        # so this doubles as the natural key -- lets chunk_and_embed rerun
        # with ignore_conflicts instead of duplicating every chunk.
        unique_together = ('start_verse', 'end_verse', 'translation')
        indexes = [
            # retrieve_chunks() orders by `embedding <=> query_vector`
            # (cosine distance), so the index must use the matching opclass.
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return f"{self.book.name} {self.start_verse.chapter}:{self.start_verse.verse_num} - {self.end_verse.chapter}:{self.end_verse.verse_num}"
    

class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200, default='Bible Discussion')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title
    

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    retrieved_verses = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

