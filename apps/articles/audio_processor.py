#!/usr/bin/env python3

from typing import List, Optional
from pydub import AudioSegment
import os
from pathlib import Path
import tempfile
from .audio_analyzer import WhisperAnalyzer
from .word_translator import TranslationService
from apps.vocabulary.models import VocabularyItem
import logging

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, 
                 audio_cache_dir: str = "audio_cache",
                 word_gap: int = 500,  # ms
                 sentence_gap: int = 1000):  # ms
        self.audio_cache_dir = Path(audio_cache_dir)
        self.audio_cache_dir.mkdir(exist_ok=True)
        self.translator = TranslationService(audio_cache_dir)
        self.word_gap = word_gap
        self.sentence_gap = sentence_gap
        
    def _check_word_status(self, word: str) -> bool:
        """检查单词是否需要解释（未掌握且未忽略）"""
        vocab_item = VocabularyItem.objects.filter(word__lemma=word).first()
        return not vocab_item or (not vocab_item.mastered and not vocab_item.ignored)
        
    def process_sentence(self, 
                        audio_file: str,
                        start_time: float,
                        end_time: float,
                        words: List[str]) -> AudioSegment:
        """处理单个句子，添加单词解释"""
        # 加载原始音频
        original_audio = AudioSegment.from_file(audio_file)
        
        # 提取句子音频
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)
        sentence_audio = original_audio[start_ms:end_ms]
        
        # 创建最终音频
        final_audio = sentence_audio
        
        # 添加间隔
        silence = AudioSegment.silent(duration=self.word_gap)
        final_audio += silence
        
        # 处理每个单词
        for word in words:
            # 检查单词状态
            if self._check_word_status(word):
                # 获取单词翻译和音频
                translation, trans_audio_path = self.translator.process_word(word)
                if translation and trans_audio_path:
                    # 添加英文单词发音
                    word_audio_path = self.translator.generate_audio(word, 'en')
                    if word_audio_path:
                        word_audio = AudioSegment.from_file(word_audio_path)
                        final_audio += word_audio
                        final_audio += silence
                    
                    # 添加中文翻译发音
                    trans_audio = AudioSegment.from_file(trans_audio_path)
                    final_audio += trans_audio
                    final_audio += silence
        
        return final_audio
    
    def process_article_audio(self, 
                            article_audio_path: str,
                            sentences_data: List[dict]) -> str:
        """处理整篇文章的音频"""
        final_audio = AudioSegment.empty()
        sentence_silence = AudioSegment.silent(duration=self.sentence_gap)
        
        for sentence_data in sentences_data:
            # 处理每个句子
            sentence_audio = self.process_sentence(
                audio_file=article_audio_path,
                start_time=sentence_data['start_time'],
                end_time=sentence_data['end_time'],
                words=sentence_data['words']
            )
            
            final_audio += sentence_audio
            final_audio += sentence_silence
        
        # 保存最终音频
        output_path = self.audio_cache_dir / f"processed_{Path(article_audio_path).name}"
        final_audio.export(str(output_path), format="mp3")
        
        return str(output_path) 