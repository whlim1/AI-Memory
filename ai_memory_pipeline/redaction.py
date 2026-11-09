"""
Sensitive data redaction functionality for AI Memory Pipeline.

This module provides functions to identify and redact sensitive information
from text before processing or storage.
"""

import re
from typing import List, Dict, Pattern


class Redactor:
    """
    A class for redacting sensitive information from text.
    
    Supports various types of sensitive data including:
    - Personal Identifiable Information (PII)
    - Financial information
    - Contact details
    """

    def __init__(self):
        """Initialize the redactor with common patterns."""
        # Common regex patterns for different types of sensitive data
        self.patterns: Dict[str, Pattern] = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
            'url': re.compile(r'https?://(?:[-\w.])+(?:[:\d]+)?/(?:[^\s])*/?'),
        }
        
        # Custom replacement strings
        self.replacements: Dict[str, str] = {
            'ssn': '[SSN_REDACTED]',
            'credit_card': '[CREDIT_CARD_REDACTED]',
            'email': '[EMAIL_REDACTED]',
            'phone': '[PHONE_REDACTED]',
            'ip_address': '[IP_ADDRESS_REDACTED]',
            'url': '[URL_REDACTED]'
        }

    def redact_text(self, text: str, sensitive_types: List[str] = None) -> str:
        """
        Redact sensitive information from text.

        Args:
            text (str): The input text to redact
            sensitive_types (List[str]): Types of sensitive data to redact.
                                        If None, all types are redacted.

        Returns:
            str: Text with sensitive information redacted
        """
        if not isinstance(text, str):
            return text
            
        if sensitive_types is None:
            sensitive_types = list(self.patterns.keys())
        
        # Filter patterns based on requested sensitive types
        filtered_patterns = {k: v for k, v in self.patterns.items() if k in sensitive_types}
        
        result_text = text
        
        # Apply redaction for each pattern
        for pattern_type, pattern in filtered_patterns.items():
            replacement = self.replacements[pattern_type]
            result_text = pattern.sub(replacement, result_text)
            
        return result_text

    def find_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """
        Find all instances of sensitive data in the text.

        Args:
            text (str): The input text to search

        Returns:
            Dict[str, List[str]]: Dictionary mapping sensitive types to found instances
        """
        if not isinstance(text, str):
            return {}
            
        found_data = {}
        
        for pattern_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                found_data[pattern_type] = list(set(matches))  # Remove duplicates
                
        return found_data

    def redact_with_context(self, text: str, sensitive_types: List[str] = None) -> str:
        """
        Redact sensitive information while preserving context.

        Args:
            text (str): The input text to redact
            sensitive_types (List[str]): Types of sensitive data to redact.
                                        If None, all types are redacted.

        Returns:
            str: Text with sensitive information redacted and context preserved
        """
        if not isinstance(text, str):
            return text
            
        # First find all sensitive data
        found_data = self.find_sensitive_data(text)
        
        # Redact each type of sensitive data
        result_text = text
        
        if sensitive_types is None:
            sensitive_types = list(self.patterns.keys())
            
        filtered_patterns = {k: v for k, v in self.patterns.items() if k in sensitive_types}
        
        for pattern_type, pattern in filtered_patterns.items():
            replacement = self.replacements[pattern_type]
            result_text = pattern.sub(replacement, result_text)
            
        return result_text


def redact_pii(text: str) -> str:
    """
    Simple function to redact PII from text.

    Args:
        text (str): The input text to redact

    Returns:
        str: Text with PII redacted
    """
    redactor = Redactor()
    return redactor.redact_text(text)


def find_pii_data(text: str) -> Dict[str, List[str]]:
    """
    Find all PII data in the text.

    Args:
        text (str): The input text to search

    Returns:
        Dict[str, List[str]]: Dictionary mapping PII types to found instances
    """
    redactor = Redactor()
    return redactor.find_sensitive_data(text)


# Example usage and testing
if __name__ == "__main__":
    sample_text = """Contact information for John Doe:
    Email: john.doe@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Credit Card: 1234-5678-9012-3456
    IP Address: 192.168.1.1
    Website: https://example.com"""
    
    print("Original text:")
    print(sample_text)
    print("\n" + "="*50)
    
    # Test redaction
    redactor = Redactor()
    redacted_text = redactor.redact_text(sample_text)
    print("Redacted text:")
    print(redacted_text)
    
    # Find sensitive data
    found_data = redactor.find_sensitive_data(sample_text)
    print("\nFound sensitive data:")
    for data_type, instances in found_data.items():
        print(f"  {data_type}: {instances}")