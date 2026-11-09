"""
Semantic summarization functionality for AI Memory Pipeline.

This module provides functions to generate semantic summaries of text content.
"""

import re
from typing import List, Dict, Tuple
from collections import Counter


class SemanticSummarizer:
    """
    A class for generating semantic summaries of text content.
    
    Uses various techniques including keyword extraction and sentence scoring
    to create meaningful summaries.
    """

    def __init__(self):
        """Initialize the summarizer with common stop words."""
        # Common English stop words (can be expanded)
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i',
            'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }

    def extract_keywords(self, text: str, num_keywords: int = 10) -> List[str]:
        """
        Extract the most important keywords from text.

        Args:
            text (str): The input text
            num_keywords (int): Number of top keywords to return

        Returns:
            List[str]: List of extracted keywords
        """
        if not isinstance(text, str) or not text.strip():
            return []
            
        # Convert to lowercase and remove punctuation
        cleaned_text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Split into words and filter out stop words
        words = [word for word in cleaned_text.split() if word not in self.stop_words]
        
        # Count frequency of each word
        word_freq = Counter(words)
        
        # Return most common words
        return [word for word, _ in word_freq.most_common(num_keywords)]

    def score_sentences(self, sentences: List[str]) -> List[Tuple[int, str]]:
        """
        Score sentences based on keyword frequency and position.

        Args:
            sentences (List[str]): List of sentences to score

        Returns:
            List[Tuple[int, str]]: List of (score, sentence) tuples sorted by score
        """
        if not sentences:
            return []
            
        # Extract keywords from all sentences combined
        all_text = ' '.join(sentences)
        keywords = self.extract_keywords(all_text, 20)
        
        scored_sentences = []
        
        for i, sentence in enumerate(sentences):
            # Score based on keyword frequency and position (first sentences get bonus)
            score = 0
            
            # Count how many keywords appear in the sentence
            sentence_lower = sentence.lower()
            for keyword in keywords:
                if keyword in sentence_lower:
                    score += 1
                    
            # Bonus points for first and last sentences
            if i == 0 or i == len(sentences) - 1:
                score += 2
                
            scored_sentences.append((score, sentence))
            
        # Sort by score (descending)
        return sorted(scored_sentences, key=lambda x: x[0], reverse=True)

    def generate_summary(self, text: str, num_sentences: int = 3) -> str:
        """
        Generate a semantic summary of the input text.

        Args:
            text (str): The input text to summarize
            num_sentences (int): Number of sentences in the summary

        Returns:
            str: Generated summary
        """
        if not isinstance(text, str) or not text.strip():
            return ""
            
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= num_sentences:
            return ' '.join(sentences)
            
        # Score sentences
        scored = self.score_sentences(sentences)
        
        # Select top sentences
        selected_sentences = [sentence for _, sentence in scored[:num_sentences]]
        
        return ' '.join(selected_sentences)

    def generate_keyword_summary(self, text: str, num_keywords: int = 10) -> str:
        """
        Generate a summary based on extracted keywords.

        Args:
            text (str): The input text to summarize
            num_keywords (int): Number of top keywords to include in summary

        Returns:
            str: Summary containing key information
        """
        if not isinstance(text, str) or not text.strip():
            return ""
            
        keywords = self.extract_keywords(text, num_keywords)
        
        # Create a simple summary with keywords
        keyword_str = ', '.join(keywords[:num_keywords])
        return f"Key topics: {keyword_str}"


def summarize_text(text: str, method: str = 'semantic', **kwargs) -> str:
    """
    Generate a summary of text using specified method.

    Args:
        text (str): The input text to summarize
        method (str): Method to use ('semantic' or 'keywords')
        **kwargs: Additional arguments for the summarization method

    Returns:
        str: Generated summary
    """
    summarizer = SemanticSummarizer()
    
    if method == 'semantic':
        return summarizer.generate_summary(text, kwargs.get('num_sentences', 3))
    elif method == 'keywords':
        return summarizer.generate_keyword_summary(text, kwargs.get('num_keywords', 10))
    else:
        raise ValueError(f"Unknown summary method: {method}")


# Example usage and testing
if __name__ == "__main__":
    sample_text = """Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. Colloquially, the term "artificial intelligence" is often used to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving". As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. A quip in Tesler's Theorem says "AI is whatever hasn't been done yet." For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology. Modern machine learning techniques are at the heart of AI. Machine learning algorithms build a model based on sample data, known as training data, in order to make predictions or decisions without being explicitly programmed to do so."""

    print("Original text:")
    print(sample_text)
    print("\n" + "="*50)
    
    # Test semantic summarization
    summarizer = SemanticSummarizer()
    summary = summarizer.generate_summary(sample_text, 3)
    print("Semantic Summary (3 sentences):")
    print(summary)
    
    # Test keyword-based summarization
    keyword_summary = summarizer.generate_keyword_summary(sample_text, 5)
    print("\nKeyword Summary:")
    print(keyword_summary)
    
    # Test with different method
    simple_summary = summarize_text(sample_text, 'semantic', num_sentences=2)
    print("\nSimple Semantic Summary (2 sentences):")
    print(simple_summary)