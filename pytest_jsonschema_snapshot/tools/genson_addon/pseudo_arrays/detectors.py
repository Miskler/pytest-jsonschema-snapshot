import re
from .base import KeyPatternDetector


class UUIDKeyDetector(KeyPatternDetector):
    """UUID ключи: 550e8400-e29b-41d4-a716-446655440000"""
    PRIORITY = 70
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.I
        )

class ISODateTimeDetector(KeyPatternDetector):
    """ISO даты и время."""
    PRIORITY = 60
    
    def __init__(self):
        super().__init__()
        # Поддерживаем различные форматы ISO
        self.date_patterns = [
            re.compile(r'^\d{4}-\d{2}-\d{2}$'),
            re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'),
        ]
        self.pattern = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$')
    
    def get_pattern_regex(self) -> str:
        return r'\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?'


class ISOCodeDetector(KeyPatternDetector):
    """ISO коды стран (2-3 буквы) или языков (en-US)."""
    PRIORITY = 50
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^[A-Z]{2,3}$|^[a-z]{2}-[A-Z]{2}$')


class HexKeyDetector(KeyPatternDetector):
    """16-ричные ключи: 0x1a3f, 0xFF."""
    PRIORITY = 40
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^0x[0-9a-f]+$', re.I)

class AlphabeticKeyDetector(KeyPatternDetector):
    """Алфавитные ключи: a, b, c, aa, ab."""
    PRIORITY = 30
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^[a-zA-Z]+$')


class NegativeNumericDetector(KeyPatternDetector):
    """Отрицательные числовые ключи."""
    PRIORITY = 20
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^-\d+$')


class NumericStringDetector(KeyPatternDetector):
    """Обычные числовые строки (исходная функциональность)."""
    PRIORITY = 10
    
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'^\d+$')
