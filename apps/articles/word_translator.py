#！/usr/bin/env python3

# translation_service.py

import os
from typing import Tuple
from mtranslate import translate
from gtts import gTTS
import hashlib
import asyncio
import aiohttp
import json
from pathlib import Path

class TranslationService:
    def __init__(self, audio_dir: str = "audio_cache"):
        """
        Initialize the translation service.
        
        Args:
            audio_dir: Directory to store cached audio files
        """
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(exist_ok=True)
        
    def _get_cache_path(self, text: str, lang: str) -> Path:
        """Get the cached audio file path for a given text."""
        # Create a unique filename based on the text and language
        filename = hashlib.md5(f"{text}_{lang}".encode()).hexdigest() + ".mp3"
        return self.audio_dir / filename

    async def translate_word(self, word: str) -> str:
        """
        Translate an English word to Chinese using async HTTP request.
        
        Args:
            word: English word to translate
            
        Returns:
            Chinese translation of the word
        """
        try:
            # Using mtranslate for translation
            translation = translate(word, 'zh-CN')
            return translation
        except Exception as e:
            print(f"Translation error: {e}")
            return ""

    def generate_audio(self, text: str, lang: str = 'zh-CN') -> str:
        """
        Generate audio file for the given text.
        
        Args:
            text: Text to convert to speech
            lang: Language code for TTS
            
        Returns:
            Path to the generated audio file
        """
        cache_path = self._get_cache_path(text, lang)
        
        # Return cached file if exists
        if cache_path.exists():
            return str(cache_path)
            
        try:
            # Generate new audio file
            tts = gTTS(text=text, lang=lang)
            tts.save(str(cache_path))
            return str(cache_path)
        except Exception as e:
            print(f"Audio generation error: {e}")
            return ""

    async def process_word(self, word: str) -> Tuple[str, str]:
        """
        Process a word: translate it and generate audio for the translation.
        
        Args:
            word: English word to process
            
        Returns:
            Tuple of (translation, audio_file_path)
        """
        # Get translation
        translation = await self.translate_word(word)
        if not translation:
            return "", ""
            
        # Generate audio
        audio_path = self.generate_audio(translation)
        return translation, audio_path

async def main():
    """Example usage of the TranslationService."""
    service = TranslationService()
    
    # Example words
    words = ["hello", "world", "computer"]
    
    for word in words:
        translation, audio_path = await service.process_word(word)
        print(f"Word: {word}")
        print(f"Translation: {translation}")
        print(f"Audio file: {audio_path}")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())