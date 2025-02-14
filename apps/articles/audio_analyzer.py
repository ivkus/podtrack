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
    def __init__(self, model_name: str = "base", spacy_model: str = "en_core_web_sm", device: str = "auto"):
        """
        Initialize Whisper analyzer with specified model
        
        Args:
            model_name: Whisper model name ("tiny", "base", "small", "medium", "large-v3")
            spacy_model: spaCy model name for sentence segmentation
            device: Device to use for inference ("auto", "cpu", "cuda")
        """
        # Initialize faster-whisper model
        compute_type = "float16" if device != "cpu" else "int8"
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type
        )
        self.nlp = spacy.load(spacy_model)

    def _convert_audio(self, audio_path: str) -> str:
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

    def _segment_into_sentences(self, whisper_segments: List[TranscriptSegment]) -> List[SentenceSegment]:
        """Convert Whisper segments into proper sentences using spaCy"""
        sentences = []
        current_words = []
        current_text = ""

        for segment in whisper_segments:
            current_text += segment.text + " "
            current_words.extend(segment.words)

        doc = self.nlp(current_text.strip())
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_start_char = sent.start_char
            sent_end_char = sent.end_char
            
            # Find words that belong to this sentence
            sentence_words = []
            current_pos = 0
            
            for word in current_words:
                word_len = len(word.text)
                if current_pos >= sent_start_char and current_pos + word_len <= sent_end_char:
                    sentence_words.append(word)
                current_pos += word_len + 1  # +1 for space
                
                if current_pos > sent_end_char:
                    break

            if sentence_words:
                sentences.append(SentenceSegment(
                    text=sent_text,
                    start=sentence_words[0].start,
                    end=sentence_words[-1].end,
                    words=sentence_words
                ))

        return sentences

    def analyze_audio(self, audio_path: str, language: str = None) -> Dict:
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
            temp_path = self._convert_audio(audio_path)
            
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
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
            sentences = self._segment_into_sentences(transcript_segments)
            
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
        '--model', 
        help='Whisper model name (tiny, base, small, medium, large-v3)',
        default='base'
    )
    parser.add_argument(
        '--language',
        help='Language code (e.g., en, zh, es)',
        default=None
    )
    parser.add_argument(
        '--device',
        help='Device to use (auto, cpu, cuda)',
        default='auto'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = WhisperAnalyzer(args.model, device=args.device)
        result = analyzer.analyze_audio(args.input, args.language)
        
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