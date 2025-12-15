import re
from .base import KeyPatternDetector
from typing import Set


class UUIDKeyDetector(KeyPatternDetector):
    """UUID ключи: 550e8400-e29b-41d4-a716-446655440000"""
    PRIORITY = 70
    COMMENT = "UUID keys in the standard format"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.I
        )

class ISODateTimeDetector(KeyPatternDetector):
    """ISO даты и время."""
    PRIORITY = 60
    COMMENT = "Datetime in ISO format"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')


class ISOCodeDetector(KeyPatternDetector):
    """ISO коды стран (2-3 буквы) или языков (en-US)."""
    PRIORITY = 50
    COMMENT = "ISO country codes (2-3 letters) and languages"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^[A-Z]{2,3}$|^[a-z]{2}-[A-Z]{2}$')


class HexKeyDetector(KeyPatternDetector):
    """16-ричные ключи: 0x1a3f, 0xFF."""
    PRIORITY = 40
    COMMENT = "16-digit numbers with the prefix 0x"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^0x[0-9a-f]+$', re.I)


class SingleLetterDetector(KeyPatternDetector):
    """Однобуквенные ключи: a, b, c."""
    PRIORITY = 35
    COMMENT = "Single-letter keys (single letters)"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^[a-zA-Z]$')


class NegativeNumericDetector(KeyPatternDetector):
    """Числовые ключи (отрицательные и положительные)."""
    PRIORITY = 30
    COMMENT = "Integers (negative and positive)"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^-?\d+$')
    
    def should_convert(self, keys: Set[str]) -> bool:
        """
        Проверяем, что все ключи - целые числа (отрицательные или положительные).
        """
        # Проверяем, что хотя бы один ключ отрицательный
        # Это важно, чтобы смешанные отрицательные/положительные числа распознавались как NegativeNumericDetector
        has_negative = any(key.startswith('-') for key in keys)
        has_positive = any(not key.startswith('-') and key.isdigit() for key in keys)
        
        # Если есть и отрицательные, и положительные, это псевдомассив
        if has_negative and has_positive:
            return True
            
        # Если только положительные, пусть NumericStringDetector обработает
        if not has_negative and has_positive:
            return False
            
        # Если только отрицательные, это псевдомассив
        if has_negative and not has_positive:
            return True
            
        return True


class NumericStringDetector(KeyPatternDetector):
    """Обычные числовые строки (исходная функциональность)."""
    PRIORITY = 32
    COMMENT = "Positive integers as strings"
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^\d+$')
