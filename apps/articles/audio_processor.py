#!/usr/bin/env python3

from typing import List, Optional
from pydub import AudioSegment
from pathlib import Path
from .dict_reader import get_dict_reader
from .tts_service import get_tts_service
from apps.vocabulary.models import VocabularyItem
import logging

logger = logging.getLogger(__name__)

class AudioProcessor:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioProcessor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, 
                 audio_cache_dir: str = "audio_cache",
                 word_gap: int = 500,  # ms
                 sentence_gap: int = 1000):  # ms
        if self._initialized:
            return
            
        self.audio_cache_dir = Path(audio_cache_dir)
        self.audio_cache_dir.mkdir(exist_ok=True)
        self.dict_reader = get_dict_reader()
        self.tts_service = get_tts_service()
        self.word_gap = word_gap
        self.sentence_gap = sentence_gap
        self._initialized = True
        
    def _check_word_status(self, word: str) -> bool:
        """检查单词是否需要解释（未掌握且未忽略）"""
        vocab_item = VocabularyItem.objects.filter(word__lemma=word).first()
        return not vocab_item or (not vocab_item.mastered and not vocab_item.ignored)
        
    def process_sentence(self, 
                        original_audio: AudioSegment,
                        start_time: float,
                        end_time: float,
                        words: List[str]) -> AudioSegment:
        """处理单个句子，添加单词解释"""
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
                # 获取单词翻译
                word_info = self.dict_reader.query(word)
                if word_info and word_info.get('translation'):
                    translation = word_info['translation']
                    
                    # 添加英文单词发音
                    word_audio_path = self.tts_service.generate_audio(word, 'en', self.audio_cache_dir)
                    if word_audio_path:
                        word_audio = AudioSegment.from_file(word_audio_path)
                        final_audio += word_audio
                        final_audio += silence
                    
                    # 添加中文翻译发音
                    trans_audio_path = self.tts_service.generate_audio(translation, 'zh', self.audio_cache_dir)
                    if trans_audio_path:
                        trans_audio = AudioSegment.from_file(trans_audio_path)
                        final_audio += trans_audio
                        final_audio += silence
        
        return final_audio
    
    def process_article_audio(self, 
                            article_audio_path: str,
                            sentences_data: List[dict]) -> str:
        """处理整篇文章的音频"""
        # 加载原始音频（只加载一次）
        original_audio = AudioSegment.from_file(article_audio_path)
        
        final_audio = AudioSegment.empty()
        sentence_silence = AudioSegment.silent(duration=self.sentence_gap)
        
        for sentence_data in sentences_data:
            # 处理每个句子
            sentence_audio = self.process_sentence(
                original_audio=original_audio,
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

def get_audio_processor() -> AudioProcessor:
    """获取音频处理器单例"""
    return AudioProcessor() 