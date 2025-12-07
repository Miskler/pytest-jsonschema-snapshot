from abc import ABC
from typing import Optional, Set
import re


class KeyPatternDetector(ABC):
    """Базовый класс для детекторов паттернов ключей."""
    
    PRIORITY: int = 0
    """Чем выше, тем приоритетнее"""
    COMMENT: str = ""
    """Комментарий для понимания цели паттерна. Будет добавлен в схему."""
    
    def __init__(self):
        self.pattern: Optional[re.Pattern] = None
        self.name: str = self.__class__.__name__
        self.comment: str = self.COMMENT
    
    def matches(self, key: str) -> bool:
        """Проверяет, соответствует ли ключ паттерну."""
        if self.pattern:
            return bool(self.pattern.match(key))
        return False
    
    def should_convert(self, keys: Set[str]) -> bool:
        """
        Должен ли словарь с такими ключами преобразовываться в patternProperties.
        По умолчанию True.
        """
        return True
    
    def get_pattern_regex(self) -> str:
        """Возвращает regex для patternProperties."""
        if self.pattern:
            pattern_str = self.pattern.pattern
            # Убираем начальные и конечные якоря если они есть
            if pattern_str.startswith('^') and pattern_str.endswith('$'):
                return pattern_str[1:-1]
            return pattern_str
        return ".*"
    
    def get_comment(self) -> str:
        """Возвращает комментарий паттерна."""
        return self.comment
