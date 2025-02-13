#!/usr/bin/env python3
import spacy
from typing import List, Dict, Optional, Tuple
import re
from difflib import SequenceMatcher
import csv
import tempfile
import os
import pytest
import argparse

class SentenceMatcher:
    def __init__(self, nlp=None):
        """Initialize the matcher with spaCy model"""
        self.nlp = nlp or spacy.load('en_core_web_sm')
        
    def load_transcript(self, transcript_file: str) -> List[str]:
        """Load and parse transcript file into sentences"""
        with open(transcript_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Use spaCy for sentence segmentation
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    def load_word_segments(self, timings_file: str) -> List[Dict]:
        """Load word timings from CSV file"""
        segments = []
        with open(timings_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                segments.append({
                    'text': row['word'],
                    'start': float(row['start']),
                    'end': float(row['end']),
                    'conf': float(row['conf'])
                })
        return segments
    
    def get_normalized_tokens(self, text: str) -> List[str]:
        """Convert text to list of normalized tokens"""
        # Remove speaker names and clean text
        text = re.sub(r'^[^:]+:', '', text).strip().lower()
        # Process with spaCy
        doc = self.nlp(text)
        # Get lemmas, excluding stop words and punctuation
        return [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    
    def calculate_edit_distance_ratio(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio using SequenceMatcher"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_matching_span(self, target_tokens: List[str], segments: List[Dict],
                          min_ratio: float = 0.5, window_size: int = 10) -> Optional[Dict]:
        """Find the best matching span in segments for the target tokens"""
        if not target_tokens or not segments:
            return None
            
        best_match = None
        best_ratio = min_ratio
        target_text = ' '.join(target_tokens)
        
        # Use sliding window approach
        for i in range(len(segments)):
            for j in range(i + 1, min(i + window_size, len(segments) + 1)):
                window_words = [seg['text'].lower() for seg in segments[i:j]]
                window_text = ' '.join(window_words)
                
                ratio = self.calculate_edit_distance_ratio(target_text, window_text)
                
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = {
                        'start': segments[i]['start'],
                        'end': segments[j-1]['end'],
                        'ratio': ratio
                    }
        
        return best_match
    
    def match_sentences(self, sentences: List[str], segments: List[Dict]) -> List[Dict]:
        """Match all sentences with their timestamps"""
        results = []
        
        for sentence in sentences:
            # Get normalized tokens for the sentence
            tokens = self.get_normalized_tokens(sentence)
            if not tokens:
                continue
                
            # Find best matching span
            match = self.find_matching_span(tokens, segments)
            
            if match:
                results.append({
                    'sentence': sentence,
                    'start': match['start'],
                    'end': match['end']
                })
        
        return results

def match_transcript_with_timings(transcript_file: str, timings_file: str) -> List[Dict]:
    """
    Match sentences from transcript with their timings in audio
    
    Args:
        transcript_file: Path to transcript text file
        timings_file: Path to CSV file with word timings
        
    Returns:
        List of dictionaries with matched sentences and their timings
    """
    matcher = SentenceMatcher()
    sentences = matcher.load_transcript(transcript_file)
    segments = matcher.load_word_segments(timings_file)
    return matcher.match_sentences(sentences, segments)

@pytest.fixture
def test_files():
    """Create temporary files for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as transcript_file:
        transcript_file.write("""
        The United States is a country.
        It has fifty states.
        The capital is Washington.
        """)
        transcript_path = transcript_file.name

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as timings_file:
        writer = csv.writer(timings_file)
        writer.writerow(['start', 'end', 'conf', 'word'])
        test_data = [
            [0.09, 0.24, 1.0, 'the'],
            [0.24, 0.63, 1.0, 'united'],
            [0.63, 1.17, 1.0, 'states'],
            [1.23, 1.41, 1.0, 'is'],
            [1.41, 1.89, 1.0, 'a'],
            [1.89, 2.34, 1.0, 'country'],
            [2.34, 2.78, 1.0, 'it'],
            [2.78, 3.12, 1.0, 'has'],
            [3.12, 3.45, 1.0, 'fifty'],
            [3.45, 3.89, 1.0, 'states'],
            [3.89, 4.23, 1.0, 'the'],
            [4.23, 4.67, 1.0, 'capital']
        ]
        writer.writerows(test_data)
        timings_path = timings_file.name

    yield transcript_path, timings_path
    
    # Cleanup
    os.unlink(transcript_path)
    os.unlink(timings_path)

@pytest.fixture
def matcher():
    return SentenceMatcher()

def test_transcript_loading(matcher, test_files):
    transcript_path, _ = test_files
    sentences = matcher.load_transcript(transcript_path)
    assert len(sentences) == 3
    assert sentences[0].strip() == "The United States is a country."

def test_word_segments_loading(matcher, test_files):
    _, timings_path = test_files
    segments = matcher.load_word_segments(timings_path)
    assert len(segments) == 12
    assert segments[0]['text'] == 'the'
    assert segments[0]['start'] == 0.09
    assert segments[0]['end'] == 0.24

def test_token_normalization(matcher):
    text = "The United States: is a country"
    tokens = matcher.get_normalized_tokens(text)
    assert 'united' in tokens
    assert 'states' in tokens
    assert 'country' in tokens
    assert 'the' not in tokens  # stop word should be removed

def test_full_matching(test_files):
    transcript_path, timings_path = test_files
    results = match_transcript_with_timings(transcript_path, timings_path)
    assert len(results) == 3
    first_match = results[0]
    assert first_match['start'] == 0.09  # start of "the"
    assert first_match['end'] == 2.34   # end of "country"

def main():
    parser = argparse.ArgumentParser(description='Match transcript sentences with audio timings')
    parser.add_argument('transcript', help='Path to transcript text file')
    parser.add_argument('timings', help='Path to CSV file with word timings')
    
    args = parser.parse_args()
    results = match_transcript_with_timings(args.transcript, args.timings)
    
    # Print results
    for match in results:
        print(f"Sentence: {match['sentence']}")
        print(f"Time: {match['start']:.2f} -> {match['end']:.2f}")
        print()

if __name__ == '__main__':
    main()