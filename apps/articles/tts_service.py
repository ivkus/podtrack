#!/usr/bin/env python3

from kokoro import KPipeline
import soundfile as sf
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)

class TTSService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TTSService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 初始化中文和英文的 pipeline
        self.zh_pipeline = KPipeline(lang_code='z')  # 中文
        self.en_pipeline = KPipeline(lang_code='a')  # 英文（美式）
        self.sample_rate = 24000
        self._initialized = True
    
    def _get_cache_path(self, text: str, lang: str, cache_dir: Path) -> Path:
        """获取音频缓存路径"""
        filename = hashlib.md5(f"{text}_{lang}".encode()).hexdigest() + ".wav"
        return cache_dir / filename
    
    def generate_audio(self, text: str, lang: str, cache_dir: Path) -> str:
        """
        生成音频文件
        
        Args:
            text: 要转换的文本
            lang: 语言代码 ('en' 或 'zh')
            cache_dir: 缓存目录
            
        Returns:
            生成的音频文件路径
        """
        cache_path = self._get_cache_path(text, lang, cache_dir)
        
        # 如果缓存存在，直接返回
        if cache_path.exists():
            return str(cache_path)
            
        try:
            # 选择合适的 pipeline
            pipeline = self.zh_pipeline if lang == 'zh' else self.en_pipeline
            voice = 'af_heart' if lang == 'zh' else 'af_heart'  # 可以根据需要更改声音
            
            # 生成音频
            generator = pipeline(text, voice=voice, speed=1)
            for _, _, audio in generator:
                sf.write(str(cache_path), audio, self.sample_rate)
                break  # 只取第一段
            
            return str(cache_path)
            
        except Exception as e:
            logger.error(f"生成音频出错: {str(e)}")
            return ""

def get_tts_service() -> TTSService:
    """获取 TTS 服务单例"""
    return TTSService() 