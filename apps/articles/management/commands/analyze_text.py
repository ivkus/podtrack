#!/usr/bin/env python3

import json
import logging
from pathlib import Path
from typing import Dict, List

import spacy
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Analyze text file and extract sentences with their lemmatized words'

    def add_arguments(self, parser):
        parser.add_argument('input', help='Input file path')
        parser.add_argument(
            '--output',
            help='Output JSON file path (optional)'
        )

    def analyze_text(self, text: str) -> List[Dict]:
        """
        Analyze text and return sentences with their lemmatized words.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of dictionaries containing sentences and their analyzed words
        """
        # Load English language model
        nlp = spacy.load('en_core_web_sm')
        
        # Define words to exclude (pronouns, numbers, etc.)
        exclude_pos = {'PRON', 'NUM', 'PROPN', 'SPACE', 'PUNCT', 'SYM', 'X'}
        
        doc = nlp(text)
        analyzed_sentences = []
        
        for sent in doc.sents:
            # Get lemmatized words with their POS tags
            words = [
                {
                    'text': token.text,
                    'lemma': token.lemma_.lower(),
                    'pos': token.pos_
                }
                for token in sent
                if (token.pos_ not in exclude_pos and 
                    not token.is_stop and
                    token.lemma_.isalpha() and  # Only alphabetic words
                    len(token.lemma_) > 1)  # Exclude single letters
            ]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_words = []
            for word in words:
                if word['lemma'] not in seen:
                    seen.add(word['lemma'])
                    unique_words.append(word)
            
            analyzed_sentences.append({
                'text': sent.text.strip(),
                'words': unique_words
            })
            
        return analyzed_sentences

    def handle(self, *args, **options):
        try:
            input_path = Path(options['input'])
            
            # Read input file
            try:
                text = input_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try different encoding if UTF-8 fails
                text = input_path.read_text(encoding='latin-1')
                
            # Analyze text
            results = self.analyze_text(text)
            
            # Format output
            output = {
                'sentences': results
            }
            
            # Write or print results
            if options['output']:
                output_path = Path(options['output'])
                output_path.write_text(
                    json.dumps(output, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Results saved to: {output_path}")
                )
            else:
                self.stdout.write(
                    json.dumps(output, ensure_ascii=False, indent=2)
                )
                
        except Exception as e:
            logger.error(f"分析文本时出错: {str(e)}", exc_info=True)
            raise 