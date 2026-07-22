from django.contrib import admin
from .models import Book, Verse, Chunk, ChatSession, ChatMessage

admin.site.register(Book)
admin.site.register(Verse)
admin.site.register(Chunk)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
