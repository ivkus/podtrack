from rest_framework import serializers
from .models import Article, Sentence, Word
from apps.vocabulary.models import VocabularyItem

class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = ['id', 'lemma']


class SentenceSerializer(serializers.ModelSerializer):
    # Only include words that are not mastered or ignored
    words = serializers.SerializerMethodField()

    class Meta:
        model = Sentence
        fields = ['id', 'content', 'order', 'start_time', 'end_time', 'words']

    def get_words(self, obj):
        # Get all words for this sentence
        words = obj.words.all()
        
        # Filter out words that are mastered or ignored
        filtered_words = []
        for word in words:
            vocab_item = VocabularyItem.objects.filter(word=word).first()
            if not vocab_item or (not vocab_item.mastered and not vocab_item.ignored):
                filtered_words.append(word)
        
        return WordSerializer(filtered_words, many=True).data


class SentenceReaderSerializer(serializers.ModelSerializer):
    # Include all words for reading
    words = WordSerializer(many=True, read_only=True)

    class Meta:
        model = Sentence
        fields = ['id', 'content', 'order', 'start_time', 'end_time', 'words']


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'text_file', 'audio_file', 
            'created_at', 'updated_at', 'processing_status'
        ]


class ArticleDetailSerializer(serializers.ModelSerializer):
    sentences = SentenceReaderSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'audio_file', 'created_at', 'updated_at', 'sentences']


class ArticleAnalysisSerializer(serializers.ModelSerializer):
    sentences = SentenceSerializer(many=True, read_only=True)
    total_words = serializers.SerializerMethodField()
    new_words = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'created_at', 
            'updated_at', 'sentences', 'total_words', 'new_words'
        ]

    def get_total_words(self, obj):
        return obj.words.count()

    def get_new_words(self, obj):
        new_words = []
        for word in obj.words.all():
            vocab_item = VocabularyItem.objects.filter(word=word).first()
            if not vocab_item or (not vocab_item.mastered and not vocab_item.ignored):
                new_words.append(word)
        return WordSerializer(new_words, many=True).data