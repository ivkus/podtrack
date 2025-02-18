import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Article
from .serializers import (
    ArticleSerializer, ArticleDetailSerializer,
    ArticleAnalysisSerializer
)
from .tasks import transcribe_audio, analyze_article, process_article_audio

logger = logging.getLogger(__name__)

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        if self.action in {'analyze', 'analysis'}:
            return ArticleAnalysisSerializer
        return ArticleSerializer

    def perform_create(self, serializer):
        article = serializer.save()
        # 不再自动开始处理
        
    @action(detail=True, methods=['post'])
    def transcribe(self, request, pk=None):
        """开始音频转写"""
        article = self.get_object()
        
        if article.transcription_status == 'processing':
            return Response(
                {"error": "文章正在转写中"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        transcribe_audio(article.id)
        return Response({"status": "转写任务已开始"})

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """开始文章分析（找出生词）"""
        article = self.get_object()
        
        if article.transcription_status != 'completed':
            return Response(
                {"error": "请先完成文章转写"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if article.analysis_status == 'processing':
            return Response(
                {"error": "文章正在分析中"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        analyze_article(article.id)
        return Response({"status": "分析任务已开始"})

    @action(detail=True, methods=['post'])
    def process_audio(self, request, pk=None):
        """开始处理音频（添加解说）"""
        article = self.get_object()
        
        if article.analysis_status != 'completed':
            return Response(
                {"error": "请先完成文章分析"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if article.audio_processing_status == 'processing':
            return Response(
                {"error": "音频正在处理中"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        process_article_audio(article.id)
        return Response({"status": "音频处理任务已开始"})

    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """获取文章分析结果"""
        article = self.get_object()
        serializer = ArticleAnalysisSerializer(article)
        return Response(serializer.data)