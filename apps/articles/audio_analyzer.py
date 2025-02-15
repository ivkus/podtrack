#!/usr/bin/env python3

from faster_whisper import WhisperModel
from typing import List, Dict, Optional
from dataclasses import dataclass
import tempfile
from pydub import AudioSegment
import os
import json
import argparse
import sys
import spacy
from dataclasses import asdict

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

class WhisperAnalyzer:
    # 类级别变量
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )
    nlp = spacy.load("en_core_web_sm")

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
        doc = cls.nlp(full_text.strip())
        
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
            segments, info = cls.model.transcribe(
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

def main():
    parser = argparse.ArgumentParser(description='Analyze audio using Whisper')
    parser.add_argument('input', help='Input audio file path')
    parser.add_argument(
        '--language',
        help='Language code (e.g., en, zh, es)',
        default=None
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        result = WhisperAnalyzer.analyze_audio(args.input, args.language)
        
        output = {
            "full_text": result["full_text"],
            "segments": [asdict(segment) for segment in result["segments"]],
            "sentences": [asdict(sentence) for sentence in result["sentences"]]
        }
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"Results saved to: {args.output}")
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 