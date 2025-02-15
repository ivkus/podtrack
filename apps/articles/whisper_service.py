#!/usr/bin/env python3

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, ClassVar

from pydub import AudioSegment

logger = logging.getLogger(__name__)

@dataclass
class Word:
    text: str
    start: float
    end: float
    probability: float

@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: List[Word]

@dataclass
class SentenceSegment:
    text: str
    start: float
    end: float
    words: List[Word]

class WhisperService:
    # 类级别变量
    _model: ClassVar[Optional['WhisperModel']] = None
    _nlp: ClassVar[Optional['Language']] = None

    @classmethod
    def _get_model(cls) -> 'WhisperModel':
        """延迟加载 Whisper 模型"""
        if cls._model is None:
            from faster_whisper import WhisperModel
            logger.info("加载 Whisper 模型...")
            cls._model = WhisperModel(
                "base",
                device="cpu",
                compute_type="int8"
            )
        return cls._model

    @classmethod
    def _get_nlp(cls) -> 'Language':
        """延迟加载 spaCy 模型"""
        if cls._nlp is None:
            import spacy
            logger.info("加载 spaCy 模型...")
            cls._nlp = spacy.load("en_core_web_sm")
        return cls._nlp

    @classmethod
    def _convert_audio(cls, audio_path: str) -> str:
        """Convert audio to format compatible with Whisper (WAV, mono, 16kHz)"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_frame_rate(16000)  # Convert to 16kHz
            audio.export(temp_path, format="wav")
            return temp_path
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise ValueError(f"Error converting audio file: {str(e)}")

    @classmethod
    def _segment_into_sentences(cls, whisper_segments: List[TranscriptSegment]) -> List[SentenceSegment]:
        """Convert Whisper segments into proper sentences using spaCy"""
        sentences = []
        all_words = []
        full_text = ""
        word_mapping = {}  # Map word start positions to Word objects
        
        # First, collect all words and build the full text
        for segment in whisper_segments:
            for word in segment.words:
                all_words.append(word)
                # Map the word's start position in the text to the Word object
                word_mapping[len(full_text)] = word
                full_text += word.text + " "
        
        # Use spaCy for sentence detection
        doc = cls._get_nlp()(full_text.strip())
        
        # Process each sentence
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:  # Skip empty sentences
                continue
                
            # Find all words in this sentence span
            sentence_words = []
            sent_start = sent.start_char
            sent_end = sent.end_char
            
            # Find the closest word start positions for this sentence
            relevant_positions = [pos for pos in word_mapping.keys() 
                                if pos <= sent_end]
            
            # Get words that belong to this sentence
            for pos in relevant_positions:
                word = word_mapping[pos]
                word_end_pos = pos + len(word.text)
                
                # Check if this word belongs to the current sentence
                if pos >= sent_start and word_end_pos <= sent_end:
                    sentence_words.append(word)
            
            if sentence_words:
                sentences.append(SentenceSegment(
                    text=sent_text,
                    start=sentence_words[0].start,
                    end=sentence_words[-1].end,
                    words=sentence_words
                ))
        
        return sentences

    @classmethod
    def analyze_audio(cls, audio_path: str, language: str = None) -> Dict:
        """
        Analyze audio file and return full transcript with timed segments
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., "en", "zh", "es")
            
        Returns:
            Dictionary containing:
            - full_text: Complete transcript
            - segments: List of TranscriptSegment objects
            - sentences: List of SentenceSegment objects
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        temp_path = None
        try:
            temp_path = cls._convert_audio(audio_path)
            
            # Transcribe with faster-whisper
            segments, info = cls._get_model().transcribe(
                temp_path,
                language=language,
                word_timestamps=True  # Enable word-level timestamps
            )
            
            # Process segments
            transcript_segments = []
            full_text = ""
            
            for segment in segments:
                words = [
                    Word(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                        probability=word.probability
                    )
                    for word in segment.words
                ]
                
                transcript_segment = TranscriptSegment(
                    text=segment.text.strip(),
                    start=segment.start,
                    end=segment.end,
                    words=words
                )
                transcript_segments.append(transcript_segment)
                full_text += segment.text + " "
            
            # Convert to proper sentences
            sentences = cls._segment_into_sentences(transcript_segments)
            
            return {
                "full_text": full_text.strip(),
                "segments": transcript_segments,
                "sentences": sentences
            }
            
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path) 