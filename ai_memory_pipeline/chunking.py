"""
Text chunking functionality for AI Memory Pipeline.

This module provides functions to split text into manageable chunks
for processing and indexing in the vector database.
"""

import re
from typing import List, Generator


def split_text_by_sentences(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks by sentence boundaries.

    Args:
        text (str): The input text to chunk
        max_chunk_size (int): Maximum size of each chunk in characters

    Returns:
        List[str]: List of text chunks
    """
    if not text or not isinstance(text, str):
        return []

    # Split by sentences using regex pattern that handles various sentence endings
    sentences = re.split(r'[.!?]+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If adding this sentence would exceed the limit, start a new chunk
        if len(current_chunk) + len(sentence) + 1 > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def split_text_by_words(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks by word boundaries.

    Args:
        text (str): The input text to chunk
        max_chunk_size (int): Maximum size of each chunk in characters

    Returns:
        List[str]: List of text chunks
    """
    if not text or not isinstance(text, str):
        return []

    words = text.split()
    chunks = []
    current_chunk = ""
    
    for word in words:
        # If adding this word would exceed the limit, start a new chunk
        if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = word
        else:
            if current_chunk:
                current_chunk += " " + word
            else:
                current_chunk = word
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def split_text_by_paragraphs(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks by paragraph boundaries.

    Args:
        text (str): The input text to chunk
        max_chunk_size (int): Maximum size of each chunk in characters

    Returns:
        List[str]: List of text chunks
    """
    if not text or not isinstance(text, str):
        return []

    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If adding this paragraph would exceed the limit, start a new chunk
        if len(current_chunk) + len(paragraph) + 2 > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def chunk_text(text: str, method: str = 'sentences', max_chunk_size: int = 1000) -> List[str]:
    """
    Chunk text using specified method.

    Args:
        text (str): The input text to chunk
        method (str): Method to use ('sentences', 'words', or 'paragraphs')
        max_chunk_size (int): Maximum size of each chunk in characters

    Returns:
        List[str]: List of text chunks
    """
    methods = {
        'sentences': split_text_by_sentences,
        'words': split_text_by_words,
        'paragraphs': split_text_by_paragraphs
    }
    
    if method not in methods:
        raise ValueError(f"Unknown chunking method: {method}")
    
    return methods[method](text, max_chunk_size)


def chunk_generator(text: str, method: str = 'sentences', max_chunk_size: int = 1000) -> Generator[str, None, None]:
    """
    Generate text chunks one at a time.

    Args:
        text (str): The input text to chunk
        method (str): Method to use ('sentences', 'words', or 'paragraphs')
        max_chunk_size (int): Maximum size of each chunk in characters

    Yields:
        str: Text chunks one at a time
    """
    chunks = chunk_text(text, method, max_chunk_size)
    for chunk in chunks:
        yield chunk


# Example usage and testing
if __name__ == "__main__":
    sample_text = """This is the first sentence. This is the second sentence! And this is the third sentence? 
    Here's a paragraph that should be handled properly. It might contain multiple sentences.
    
    Another paragraph with different content. This one also has several sentences to demonstrate chunking functionality."""
    
    print("Original text length:", len(sample_text))
    
    # Test different chunking methods
    chunks_sentences = split_text_by_sentences(sample_text, 200)
    print(f"\nSentences method - Chunks: {len(chunks_sentences)}")
    for i, chunk in enumerate(chunks_sentences):
        print(f"Chunk {i+1}: {chunk}")
    
    chunks_words = split_text_by_words(sample_text, 200)
    print(f"\nWords method - Chunks: {len(chunks_words)}")
    for i, chunk in enumerate(chunks_words):
        print(f"Chunk {i+1}: {chunk}")