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
from dataclasses import dataclass

@dataclass
class WordSegment:
    text: str
    start: float
    end: float
    conf: float

@dataclass
class SentenceMatch:
    sentence: str
    start: float
    end: float
    ratio: float

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
    
    def load_word_segments(self, timings_file: str) -> List[WordSegment]:
        """Load word timings from CSV file"""
        segments = []
        with open(timings_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                segments.append(WordSegment(
                    text=row['word'],
                    start=float(row['start']),
                    end=float(row['end']),
                    conf=float(row['conf'])
                ))
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
    
    def find_matching_span(self, target_tokens: List[str], segments: List[WordSegment],
                          min_ratio: float = 0.5, window_size: int = 10) -> Optional[Dict]:
        """
        在语音识别的时间段中寻找最匹配目标词序列的时间跨度
        
        Args:
            target_tokens: 目标句子的标准化词序列
            segments: 语音识别结果的时间段列表，每个段包含单词和时间信息
            min_ratio: 最小匹配比率阈值，默认0.5
            window_size: 滑动窗口大小，默认10个词
            
        Returns:
            包含最佳匹配时间段的字典，如果没有找到匹配则返回None
        """
        # 输入验证
        if not target_tokens or not segments:
            return None
            
        best_match = None  # 存储最佳匹配结果
        best_ratio = min_ratio  # 当前最佳匹配比率
        target_text = ' '.join(target_tokens)  # 将目标词序列连接成文本
        
        # 使用滑动窗口方法遍历所有可能的时间段组合
        for i in range(len(segments)):  # i是窗口起始位置
            # j是窗口结束位置，范围从i+1到min(i+window_size,总长度)
            for j in range(i + 1, min(i + window_size, len(segments) + 1)):
                # 提取当前窗口中的所有词并转换为小写
                window_words = [seg.text.lower() for seg in segments[i:j]]
                window_text = ' '.join(window_words)  # 连接成文本
                
                # 计算当前窗口文本与目标文本的相似度
                ratio = self.calculate_edit_distance_ratio(target_text, window_text)
                
                # 如果找到更好的匹配，更新最佳匹配信息
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = {
                        'start': segments[i].start,  # 窗口起始时间
                        'end': segments[j-1].end,    # 窗口结束时间
                        'ratio': ratio               # 匹配相似度
                    }
        
        return best_match
    
    def match_sentences(self, sentences: List[str], segments: List[WordSegment]) -> List[SentenceMatch]:
        """
        将文本中的所有句子与音频时间段进行匹配
        
        Args:
            sentences: 文本句子列表
            segments: 语音识别结果的时间段列表
            
        Returns:
            包含每个句子及其对应时间段的SentenceMatch列表
        """
        results = []
        
        for sentence in sentences:
            tokens = self.get_normalized_tokens(sentence)
            if not tokens:  # 如果句子没有有效词，跳过
                continue
                
            match = self.find_matching_span(tokens, segments)
            
            if match:
                results.append(SentenceMatch(
                    sentence=sentence,
                    start=match['start'],
                    end=match['end'],
                    ratio=match['ratio']
                ))
        
        return results

def match_transcript_with_timings(transcript_file: str, timings_file: str) -> List[SentenceMatch]:
    """
    Match sentences from transcript with their timings in audio
    
    Args:
        transcript_file: Path to transcript text file
        timings_file: Path to CSV file with word timings
        
    Returns:
        List of SentenceMatch objects with matched sentences and their timings
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
    assert segments[0].text == 'the'
    assert segments[0].start == 0.09
    assert segments[0].end == 0.24

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
    assert first_match.start == 0.09  # start of "the"
    assert first_match.end == 2.34   # end of "country"

def main():
    parser = argparse.ArgumentParser(description='Match transcript sentences with audio timings')
    parser.add_argument('transcript', help='Path to transcript text file')
    parser.add_argument('timings', help='Path to CSV file with word timings')
    
    args = parser.parse_args()
    results = match_transcript_with_timings(args.transcript, args.timings)
    
    # Print results
    for match in results:
        print(f"Sentence: {match.sentence}")
        print(f"Time: {match.start:.2f} -> {match.end:.2f}")
        print(f"Match ratio: {match.ratio:.2f}")
        print()

if __name__ == '__main__':
    main()