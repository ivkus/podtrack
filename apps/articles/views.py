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
import logging
import re
import unicodedata

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

    def _clean_word(self, word: str) -> str:
        """清理单词文本，移除不需要的字符

        Args:
            word: 原始单词文本

        Returns:
            str: 清理后的单词文本
        """
        # 转换为小写
        word = word.lower()
        
        # 标准化 Unicode 字符（如将 "café" 转换为 "cafe"）
        word = unicodedata.normalize('NFKD', word).encode('ASCII', 'ignore').decode('ASCII')
        
        # 移除标点符号和特殊字符
        # 保留连字符和撇号，因为它们可能是单词的一部分（如 "it's", "well-known"）
        word = re.sub(r'[^\w\s\'-]', '', word)
        
        # 处理连字符
        # 如果连字符在单词中间，保留它；如果在开头或结尾，删除它
        word = re.sub(r'^-+|-+$', '', word)
        
        # 处理撇号
        # 保留单词中的撇号（如 "don't"），但删除多余的撇号
        word = re.sub(r"'+", "'", word)
        word = re.sub(r"^'+|'+$", '', word)
        
        # 去除首尾空格，将多个空格替换为单个空格
        word = ' '.join(word.split())
        
        return word

    def _filter_word(self, word_text: str) -> tuple[bool, str]:
        """检查单词是否应该被包含在词汇表中，并返回过滤原因

        Args:
            word_text: 要检查的单词

        Returns:
            tuple: (是否通过过滤, 过滤原因)
        """
        # 预处理文本
        word_text = self._clean_word(word_text)
        
        # 如果清理后为空，直接返回
        if not word_text:
            return False, "清理后为空"
        
        doc = self.nlp(word_text)
        
        # 检查是否为单个词
        if len(doc) != 1:
            # 记录更详细的信息以便调试
            tokens = [f"'{token.text}' ({token.pos_})" for token in doc]
            reason = f"不是单个词 (tokens: {', '.join(tokens)})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        token = doc[0]
        
        # 检查词性
        if token.pos_ in self.exclude_pos:
            reason = f"词性被排除 (POS: {token.pos_})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        # 检查是否为停用词
        if token.is_stop:
            reason = "是停用词"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        # 检查是否只包含字母
        if not token.lemma_.isalpha():
            reason = "包含非字母字符"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        # 检查长度
        if len(token.lemma_) <= 1:
            reason = f"词太短 (length: {len(token.lemma_)})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        logger.debug(f"接受词: '{word_text}' (lemma: {token.lemma_}, POS: {token.pos_})")
        return True, "accepted"

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
                print(f"Processing sentence {idx}: {sent.text}")
                print(f"Time: {sent.start}s - {sent.end}s")
                
                sentence = Sentence.objects.create(
                    article=article,
                    content=sent.text,
                    order=idx,
                    start_time=sent.start,
                    end_time=sent.end
                )
                print(f"Created sentence object with id {sentence.id}")

                # 过滤并处理单词
                print(f"Processing words for sentence {idx}:")
                for word_info in sent.words:
                    word_text = word_info.text.lower()
                    print(f"  - Checking word: {word_text}")
                    should_include, reason = self._filter_word(word_text)
                    
                    if should_include:
                        word, created = Word.objects.get_or_create(lemma=word_text)
                        print(f"    - {'Created' if created else 'Found'} word object with lemma: {word_text}")
                        word.sentences.add(sentence)
                        word.articles.add(article)
                        vocab_item, vocab_created = VocabularyItem.objects.get_or_create(word=word)
                        print(f"    - {'Created' if vocab_created else 'Found'} vocabulary item")
                        logger.info(
                            f"添加词 '{word_text}' 到文章 {article.id} "
                            f"(新词: {created}, 新词汇项: {vocab_created})"
                        )
                    else:
                        print(f"    - Word filtered out: {word_text} - {reason}")
                        logger.debug(
                            f"在文章 {article.id} 中跳过词 '{word_text}' - {reason}"
                        )
                print("---")

            serializer = self.get_serializer(article)
            return Response(serializer.data, status=201)

        except Exception as e:
            logger.error(f"创建文章时出错: {str(e)}", exc_info=True)
            # 如果出错，删除已创建的文章
            if 'article' in locals():
                article.delete()
            return Response(
                {'error': str(e)},
                status=500
            )