from huey.contrib.djhuey import db_task 
from .audio_analyzer import WhisperAnalyzer
from .audio_processor import AudioProcessor
from .models import Article, Sentence, Word
from apps.vocabulary.models import VocabularyItem
import logging
import re
import unicodedata
import spacy
import asyncio
from asgiref.sync import sync_to_async
from django.db import transaction

logger = logging.getLogger(__name__)

class WordProcessor:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.exclude_pos = {'PRON', 'NUM', 'PROPN', 'SPACE', 'PUNCT', 'SYM', 'X'}

    def clean_word(self, word: str) -> str:
        """清理单词文本，移除不需要的字符"""
        # 转换为小写
        word = word.lower()
        
        # 标准化 Unicode 字符
        word = unicodedata.normalize('NFKD', word).encode('ASCII', 'ignore').decode('ASCII')
        
        # 移除标点符号和特殊字符，保留连字符和撇号
        word = re.sub(r'[^\w\s\'-]', '', word)
        
        # 处理连字符
        word = re.sub(r'^-+|-+$', '', word)
        
        # 处理撇号
        word = re.sub(r"'+", "'", word)
        word = re.sub(r"^'+|'+$", '', word)
        
        # 清理空格
        word = ' '.join(word.split())
        
        # 清理标点
        word = re.sub(r'[.,?!]+$', '', word)
        word = re.sub(r'^[.,?!]+', '', word)
        word = word.strip()
        
        # 验证单词有效性
        if (word.startswith('-') or 
            word.endswith('-') or 
            word == '-' or 
            '--' in word):
            return ''
        
        return word

    def filter_word(self, word_text: str) -> tuple[bool, str]:
        """检查单词是否应该被包含在词汇表中"""
        word_text = self.clean_word(word_text)
        
        if not word_text:
            return False, "清理后为空"
        
        doc = self.nlp(word_text)
        
        if len(doc) != 1:
            tokens = [f"'{token.text}' ({token.pos_})" for token in doc]
            reason = f"不是单个词 (tokens: {', '.join(tokens)})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        token = doc[0]
        
        if token.pos_ in self.exclude_pos:
            reason = f"词性被排除 (POS: {token.pos_})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        if token.is_stop:
            reason = "是停用词"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        if len(token.lemma_) <= 1:
            reason = f"词太短 (length: {len(token.lemma_)})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        logger.debug(f"接受词: '{word_text}' (lemma: {token.lemma_}, POS: {token.pos_})")
        return True, token.lemma_

@db_task()
def process_audio_file(article_id: int):
    """处理文章的音频文件"""
    try:
        logger.info(f"开始处理文章 {article_id}")
        
        # 使用事务来确保数据一致性
        with transaction.atomic():
            article = Article.objects.get(id=article_id)
            article.processing_status = 'processing'
            article.save()
            
            word_processor = WordProcessor()
            
            # 使用 WhisperAnalyzer 分析音频
            analyzer = WhisperAnalyzer(model_name="base")
            result = analyzer.analyze_audio(article.audio_file.path)

            # 更新文章内容
            article.content = result["full_text"]
            article.save()

            # 保存句子和时间戳信息
            sentences_data = []
            for idx, sent in enumerate(result["sentences"]):
                # 创建句子对象
                sentence = Sentence.objects.create(
                    article=article,
                    content=sent.text,
                    order=idx,
                    start_time=sent.start,
                    end_time=sent.end
                )

                # 处理单词
                sentence_words = []
                for word_info in sent.words:
                    word_text = word_info.text.lower()
                    should_include, lemma = word_processor.filter_word(word_text)
                    
                    if should_include:
                        # 创建或获取单词对象
                        word, created = Word.objects.get_or_create(lemma=lemma)
                        word.sentences.add(sentence)
                        word.articles.add(article)
                        sentence_words.append(lemma)
                        
                        vocab_item, vocab_created = VocabularyItem.objects.get_or_create(word=word)
                        logger.info(
                            f"添加词 '{lemma}' 到文章 {article.id} "
                            f"(新词: {created}, 新词汇项: {vocab_created})"
                        )
                
                # 收集句子数据用于音频处理
                sentences_data.append({
                    'start_time': sent.start,
                    'end_time': sent.end,
                    'words': sentence_words
                })

            # 处理音频
            audio_processor = AudioProcessor()
            
            # 创建新的事件循环来运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processed_audio_path = loop.run_until_complete(
                    audio_processor.process_article_audio(
                        article.audio_file.path,
                        sentences_data
                    )
                )
            finally:
                loop.close()
            
            # 更新文章的处理后音频路径
            article.processed_audio_file = processed_audio_path
            article.processing_status = 'completed'
            article.save()

    except Exception as e:
        logger.error(f"处理音频文件时出错: {str(e)}", exc_info=True)
        if 'article' in locals():
            article.processing_status = 'failed'
            article.save() 