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
import chardet

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

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

    def create(self, request, *args, **kwargs):
        try:
            title = request.data.get('title')
            text_file = request.FILES.get('textFile')
            audio_file = request.FILES.get('audioFile')

            if not all([title, text_file, audio_file]):
                return Response(
                    {'error': 'Missing required fields'},
                    status=400
                )

            # 读取文本文件内容
            raw_content = text_file.read()
            # 检测编码
            encoding = chardet.detect(raw_content)['encoding']
            content = raw_content.decode(encoding)

            # 创建文章记录
            article = Article.objects.create(
                title=title,
                text_file=text_file,
                audio_file=audio_file,
                content=content
            )

            serializer = self.get_serializer(article)
            return Response(serializer.data, status=201)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )