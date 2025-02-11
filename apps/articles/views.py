from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Article, Sentence, Word
from .serializers import (
    ArticleSerializer, 
    ArticleDetailSerializer,  # 导入包含sentences的序列化器
    ArticleAnalysisSerializer
)
from apps.vocabulary.models import VocabularyItem
from .text_analyzer import PodcastTextAnalyzer

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()

    def get_serializer_class(self):
        # 根据不同的动作使用不同的序列化器
        if self.action == 'list':
            return ArticleSerializer
        elif self.action == 'retrieve':
            return ArticleDetailSerializer  # 获取单篇文章时使用这个
        return ArticleSerializer

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        article = self.get_object()
        analyzer = PodcastTextAnalyzer()
        
        # Analyze the article
        analyzed_sentences = analyzer.analyze_text(article.content)
        
        # Process each sentence
        for index, sent_data in enumerate(analyzed_sentences):
            # Create sentence
            sentence = Sentence.objects.create(
                article=article,
                content=sent_data['text'],
                order=index
            )
            
            # Process words
            for lemma in sent_data['words']:
                word, _ = Word.objects.get_or_create(lemma=lemma)
                word.sentences.add(sentence)
                word.articles.add(article)
                
                # Create vocabulary item if doesn't exist
                VocabularyItem.objects.get_or_create(word=word)
        
        serializer = ArticleAnalysisSerializer(article)
        return Response(serializer.data)