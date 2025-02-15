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
from .audio_analyzer import WhisperAnalyzer
import spacy
import os

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

    def _filter_word(self, word_text: str) -> bool:
        """检查单词是否应该被包含在词汇表中"""
        doc = self.nlp(word_text)
        if len(doc) != 1:  # 确保是单个词
            return False
        
        token = doc[0]
        return (
            token.pos_ not in self.exclude_pos and 
            not token.is_stop and
            token.lemma_.isalpha() and  # 只包含字母
            len(token.lemma_) > 1  # 排除单字母
        )

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
            audio_file = request.FILES.get('audioFile')

            if not all([title, audio_file]):
                return Response(
                    {'error': 'Missing required fields'},
                    status=400
                )

            # 先创建文章记录，保存音频文件
            article = Article.objects.create(
                title=title,
                audio_file=audio_file
            )

            # 使用 WhisperAnalyzer 分析音频
            analyzer = WhisperAnalyzer(model_name="base")
            result = analyzer.analyze_audio(article.audio_file.path)

            # 更新文章内容
            article.content = result["full_text"]
            article.save()

            # 保存句子和时间戳信息
            for idx, sent in enumerate(result["sentences"]):
                sentence = Sentence.objects.create(
                    article=article,
                    content=sent.text,
                    order=idx,
                    start_time=sent.start,
                    end_time=sent.end
                )

                # 过滤并处理单词
                for word_info in sent.words:
                    word_text = word_info.text.lower()
                    if self._filter_word(word_text):
                        word, _ = Word.objects.get_or_create(lemma=word_text)
                        word.sentences.add(sentence)
                        word.articles.add(article)
                        VocabularyItem.objects.get_or_create(word=word)

            serializer = self.get_serializer(article)
            return Response(serializer.data, status=201)

        except Exception as e:
            # 如果出错，删除已创建的文章
            if 'article' in locals():
                article.delete()
            return Response(
                {'error': str(e)},
                status=500
            )