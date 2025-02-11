# text_analyzer.py

import spacy
from typing import List, Dict
import argparse
import json
import sys

class PodcastTextAnalyzer:
    def __init__(self):
        # Load English language model
        self.nlp = spacy.load('en_core_web_sm')
        
        # Define words to exclude (pronouns, numbers, etc.)
        self.exclude_pos = {'PRON', 'NUM', 'PROPN', 'SPACE', 'PUNCT', 'SYM', 'X'}
        
    def analyze_text(self, text: str) -> List[Dict]:
        """
        Analyze podcast text and return sentences with their lemmatized words.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of dictionaries containing sentences and their analyzed words
        """
        doc = self.nlp(text)
        analyzed_sentences = []
        
        for sent in doc.sents:
            # Get lemmatized words excluding unwanted POS
            words = [
                token.lemma_.lower()
                for token in sent
                if (token.pos_ not in self.exclude_pos and 
                    not token.is_stop and
                    token.lemma_.isalpha() and  # Only alphabetic words
                    len(token.lemma_) > 1)  # Exclude single letters
            ]
            
            # Remove duplicates while preserving order
            unique_words = list(dict.fromkeys(words))
            
            analyzed_sentences.append({
                'text': sent.text.strip(),
                'words': unique_words
            })
            
        return analyzed_sentences

def main():
    parser = argparse.ArgumentParser(description='Analyze podcast text')
    parser.add_argument('input', help='Input text or file path')
    parser.add_argument(
        '--is-file', 
        action='store_true',
        help='Treat input as file path'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Read input text
        if args.is_file:
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    text = f.read()
            except UnicodeDecodeError:
                # Try different encoding if UTF-8 fails
                with open(args.input, 'r', encoding='latin-1') as f:
                    text = f.read()
        else:
            text = args.input
            
        # Analyze text
        analyzer = PodcastTextAnalyzer()
        results = analyzer.analyze_text(text)
        
        # Format output
        output = {
            'sentences': results
        }
        
        # Write or print results
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
