from rest_framework import viewsets
from rest_framework.response import Response
from .models import Article
from .serializers import (
    ArticleSerializer, 
    ArticleDetailSerializer,  # 导入包含sentences的序列化器
)
from apps.vocabulary.models import VocabularyItem
import spacy
import logging
from .tasks import process_audio_file

logger = logging.getLogger(__name__)

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    nlp = spacy.load('en_core_web_sm')
    exclude_pos = {'PRON', 'NUM', 'PROPN', 'SPACE', 'PUNCT', 'SYM', 'X'}

    def get_serializer_class(self):
        # 根据不同的动作使用不同的序列化器
        if self.action == 'list':
            return ArticleSerializer
        elif self.action == 'retrieve':
            return ArticleDetailSerializer  # 获取单篇文章时使用这个
        return ArticleSerializer

    def create(self, request, *args, **kwargs):
        try:
            title = request.data.get('title')
            audio_file = request.FILES.get('audioFile')

            if not all([title, audio_file]):
                return Response(
                    {'error': 'Missing required fields'},
                    status=400
                )

            # 创建文章记录，保存音频文件
            article = Article.objects.create(
                title=title,
                audio_file=audio_file,
                processing_status='processing'
            )

            # 启动异步处理任务
            process_audio_file(article.id)

            serializer = self.get_serializer(article)
            return Response(serializer.data, status=201)

        except Exception as e:
            logger.error(f"创建文章时出错: {str(e)}", exc_info=True)
            if 'article' in locals():
                article.delete()
            return Response(
                {'error': str(e)},
                status=500
            )