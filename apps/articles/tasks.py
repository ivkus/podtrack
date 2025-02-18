import logging

from django.db import transaction
from huey.contrib.djhuey import db_task

from apps.vocabulary.models import VocabularyItem

from .whisper_service import WhisperService
from .audio_process_service import AudioProcessService
from .models import Article, Sentence, Word

logger = logging.getLogger(__name__)

class WordProcessService:
    _nlp = None
    exclude_pos = {'PRON', 'NUM', 'PROPN', 'SPACE', 'PUNCT', 'SYM', 'X'}

    @classmethod
    def _get_nlp(cls):
        """延迟加载 spaCy 模型"""
        if cls._nlp is None:
            import spacy
            logger.info("加载 spaCy 模型...")
            cls._nlp = spacy.load('en_core_web_sm')
        return cls._nlp

    @classmethod
    def filter_word(cls, word_text: str) -> tuple[bool, str]:
        """检查单词是否应该被包含在词汇表中"""
        # 延迟加载并使用 spaCy 处理文本
        doc = cls._get_nlp()(word_text.strip().lower())
        
        if len(doc) != 1:
            tokens = [f"'{token.text}' ({token.pos_})" for token in doc]
            reason = f"不是单个词 (tokens: {', '.join(tokens)})"
            logger.debug(f"过滤掉词: '{word_text}' - {reason}")
            return False, reason
        
        token = doc[0]
        
        if token.pos_ in cls.exclude_pos:
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
def transcribe_audio(article_id: int):
    """转写文章的音频文件为文字"""
    try:
        logger.info(f"开始转写文章 {article_id}")
        
        # 使用事务来确保数据一致性
        with transaction.atomic():
            article = Article.objects.get(id=article_id)
            article.transcription_status = 'processing'
            article.save()
            
            # 使用 WhisperService 分析音频
            result = WhisperService.analyze_audio(article.audio_file.path)

            # 更新文章内容
            article.content = result["full_text"]
            
            # 保存句子和时间戳信息
            for idx, sent in enumerate(result["sentences"]):
                # 创建句子对象
                Sentence.objects.create(
                    article=article,
                    content=sent.text,
                    order=idx,
                    start_time=sent.start,
                    end_time=sent.end
                )
            
            article.transcription_status = 'completed'
            article.save()

    except Exception as e:
        logger.error(f"转写音频文件时出错: {str(e)}", exc_info=True)
        if 'article' in locals():
            article.transcription_status = 'failed'
            article.save()

@db_task()
def analyze_article(article_id: int):
    """分析文章内容，找出生词"""
    try:
        logger.info(f"开始分析文章 {article_id}")
        
        with transaction.atomic():
            article = Article.objects.get(id=article_id)
            article.analysis_status = 'processing'
            article.save()
            
            # 处理每个句子中的单词
            for sentence in article.sentences.all():
                # 使用 WhisperService 的 words 属性获取单词列表
                for word_text in sentence.content.split():  # 简单按空格分词
                    word_text = word_text.lower()
                    should_include, lemma = WordProcessService.filter_word(word_text)
                    
                    if should_include:
                        # 创建或获取单词对象
                        word, created = Word.objects.get_or_create(lemma=lemma)
                        word.sentences.add(sentence)
                        word.articles.add(article)
                        
                        vocab_item, vocab_created = VocabularyItem.objects.get_or_create(word=word)
                        logger.info(
                            f"添加词 '{lemma}' 到文章 {article.id} "
                            f"(新词: {created}, 新词汇项: {vocab_created})"
                        )
            
            article.analysis_status = 'completed'
            article.save()

    except Exception as e:
        logger.error(f"分析文章时出错: {str(e)}", exc_info=True)
        if 'article' in locals():
            article.analysis_status = 'failed'
            article.save()

@db_task()
def process_article_audio(article_id: int):
    """处理文章音频，添加单词解释"""
    try:
        logger.info(f"开始处理文章音频 {article_id}")
        
        with transaction.atomic():
            article = Article.objects.get(id=article_id)
            article.audio_processing_status = 'processing'
            article.save()
            
            # 收集句子数据
            sentences_data = []
            for sentence in article.sentences.all():
                # 获取句子中的生词
                words = []
                for word in sentence.words.all():
                    vocab_item = VocabularyItem.objects.filter(word=word).first()
                    if not vocab_item or (not vocab_item.mastered and not vocab_item.ignored):
                        words.append(word.lemma)
                
                sentences_data.append({
                    'start_time': sentence.start_time,
                    'end_time': sentence.end_time,
                    'words': words
                })
            
            # 处理音频
            processed_audio_path = AudioProcessService.process_article_audio(
                article.audio_file.path,
                sentences_data
            )
            
            # 更新文章的处理后音频路径
            article.processed_audio_file = processed_audio_path
            article.audio_processing_status = 'completed'
            article.save()

    except Exception as e:
        logger.error(f"处理文章音频时出错: {str(e)}", exc_info=True)
        if 'article' in locals():
            article.audio_processing_status = 'failed'
            article.save() 