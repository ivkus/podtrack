#!/usr/bin/env python3

# translation_service.py

from typing import Tuple
from pathlib import Path
from .dict_reader import get_dict_reader
from .tts_service import get_tts_service
import logging

logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self, audio_dir: str = "audio_cache"):
        """
        Initialize the translation service.
        
        Args:
            audio_dir: Directory to store cached audio files
        """
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(exist_ok=True)
        self.dict_reader = get_dict_reader()
        self.tts_service = get_tts_service()

    def translate_word(self, word: str) -> str:
        """
        Translate an English word to Chinese using the dictionary.
        
        Args:
            word: English word to translate
            
        Returns:
            Chinese translation of the word
        """
        try:
            word_info = self.dict_reader.query(word)
            if word_info and word_info.get('translation'):
                return word_info['translation']
            return ""
        except Exception as e:
            logger.error(f"翻译出错: {str(e)}")
            return ""

    def generate_audio(self, text: str, lang: str = 'zh') -> str:
        """
        Generate audio file for the given text.
        
        Args:
            text: Text to convert to speech
            lang: Language code ('en' or 'zh')
            
        Returns:
            Path to the generated audio file
        """
        return self.tts_service.generate_audio(text, lang, self.audio_dir)

    def process_word(self, word: str) -> Tuple[str, str]:
        """
        Process a word: translate it and generate audio for the translation.
        
        Args:
            word: English word to process
            
        Returns:
            Tuple of (translation, audio_file_path)
        """
        # Get translation
        translation = self.translate_word(word)
        if not translation:
            return "", ""
            
        # Generate audio
        audio_path = self.generate_audio(translation, 'zh')
        return translation, audio_path

def main():
    """Example usage of the TranslationService."""
    service = TranslationService()
    
    # Example words
    words = ["hello 世界", "world", "你好"]
    
    for word in words:
        translation, audio_path = service.process_word(word)
        print(f"Word: {word}")
        print(f"Translation: {translation}")
        print(f"Audio file: {audio_path}")
        print("---")

if __name__ == "__main__":
    main()