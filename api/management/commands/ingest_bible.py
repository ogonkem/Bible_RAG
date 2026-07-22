import json
from django.core.management.base import BaseCommand
from api.models import Book, Verse

OT_BOOKS = {
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges",
    "Ruth","1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles",
    "2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
    "Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations",
    "Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah",
    "Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi",
}

class Command(BaseCommand):
    help = 'Ingest Bible verses from JSON (kjv, dby)'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, help='kjv or dby')

    def handle(self, *args, **options):
        source = options['source'].lower()
        filepath = f'data/raw/{source}.json'
        translation_code = source.upper()

        self.stdout.write(f"Loading {translation_code} from {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            bible_data = json.load(f)

        verse_objects = []
        for book_name, chapters in bible_data.items():
            testament = 'OT' if book_name in OT_BOOKS else 'NT'
            book, _ = Book.objects.get_or_create(
                name=book_name,
                defaults={'testament': testament, 'chapters': len(chapters)}
            )
            for chapter_num, verses in chapters.items():
                for verse_num, text in verses.items():
                    verse_objects.append(Verse(
                        book=book,
                        chapter=int(chapter_num),
                        verse_num=int(verse_num),
                        text=text,
                        translation=translation_code,
                    ))
            if len(verse_objects) >= 1000:
                Verse.objects.bulk_create(verse_objects, batch_size=500, ignore_conflicts=True)
                verse_objects = []

        if verse_objects:
            Verse.objects.bulk_create(verse_objects, batch_size=500, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"{translation_code} ingestion complete!"))
