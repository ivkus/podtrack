#!/usr/bin/env python3

import hashlib
import logging
from pathlib import Path
from typing import Optional, ClassVar

import soundfile as sf

logger = logging.getLogger(__name__)

class TTSService:
    # 类级别的变量
    _zh_pipeline: ClassVar[Optional['KPipeline']] = None
    _en_pipeline: ClassVar[Optional['KPipeline']] = None
    sample_rate = 24000
    
    @classmethod
    def _get_zh_pipeline(cls) -> 'KPipeline':
        """延迟初始化中文 pipeline"""
        if cls._zh_pipeline is None:
            from kokoro import KPipeline
            logger.info("初始化中文 TTS pipeline...")
            cls._zh_pipeline = KPipeline(lang_code='z')
        return cls._zh_pipeline
    
    @classmethod
    def _get_en_pipeline(cls) -> 'KPipeline':
        """延迟初始化英文 pipeline"""
        if cls._en_pipeline is None:
            from kokoro import KPipeline
            logger.info("初始化英文 TTS pipeline...")
            cls._en_pipeline = KPipeline(lang_code='a')
        return cls._en_pipeline
    
    @classmethod
    def _get_cache_path(cls, text: str, lang: str, cache_dir: Path) -> Path:
        """获取音频缓存路径"""
        filename = hashlib.md5(f"{text}_{lang}".encode()).hexdigest() + ".wav"
        return cache_dir / filename
    
    @classmethod
    def generate_audio(cls, text: str, lang: str, cache_dir: Path) -> str:
        """
        生成音频文件
        
        Args:
            text: 要转换的文本
            lang: 语言代码 ('en' 或 'zh')
            cache_dir: 缓存目录
            
        Returns:
            生成的音频文件路径
        """
        cache_path = cls._get_cache_path(text, lang, cache_dir)
        
        # 如果缓存存在，直接返回
        if cache_path.exists():
            return str(cache_path)
            
        try:
            # 选择合适的 pipeline
            pipeline = cls._get_zh_pipeline() if lang == 'zh' else cls._get_en_pipeline()
            voice = 'af_heart' if lang == 'zh' else 'af_heart'  # 可以根据需要更改声音
            
            # 生成音频
            generator = pipeline(text, voice=voice, speed=1)
            for _, _, audio in generator:
                sf.write(str(cache_path), audio, cls.sample_rate)
                break  # 只取第一段
            
            return str(cache_path)
            
        except Exception as e:
            logger.error(f"生成音频出错: {str(e)}")
            return ""
