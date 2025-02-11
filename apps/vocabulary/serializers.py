from rest_framework import serializers
from .models import VocabularyItem
from apps.articles.models import Word

class WordDetailSerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()
    sentence_count = serializers.SerializerMethodField()

    class Meta:
        model = Word
        fields = ['id', 'lemma', 'article_count', 'sentence_count']

    def get_article_count(self, obj):
        return obj.articles.count()

    def get_sentence_count(self, obj):
        return obj.sentences.count()


class VocabularyItemSerializer(serializers.ModelSerializer):
    word = WordDetailSerializer(read_only=True)
    usage_examples = serializers.SerializerMethodField()

    class Meta:
        model = VocabularyItem
        fields = [
            'id', 'word', 'mastered', 'ignored', 
            'last_reviewed', 'usage_examples'
        ]

    def get_usage_examples(self, obj):
        # 获取包含这个单词的前3个句子作为使用示例
        sentences = obj.word.sentences.all()[:3]
        return [sentence.content for sentence in sentences]


class VocabularyStatsSerializer(serializers.Serializer):
    total_words = serializers.IntegerField()
    mastered_words = serializers.IntegerField()
    learning_words = serializers.IntegerField()
    ignored_words = serializers.IntegerField()
    mastery_rate = serializers.FloatField()