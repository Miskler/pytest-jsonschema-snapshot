from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set
import re


class KeyPatternDetector(ABC):
    """Базовый класс для детекторов паттернов ключей."""
    
    PRIORITY: int = 0  # Чем выше, тем приоритетнее
    
    def __init__(self):
        self.pattern: Optional[re.Pattern] = None
        self.name: str = self.__class__.__name__
    
    def matches(self, key: str) -> bool:
        """Проверяет, соответствует ли ключ паттерну."""
        return bool(self.pattern.match(key))
    
    def should_convert(self, keys: Set[str]) -> bool:
        """
        Должен ли словарь с такими ключами преобразовываться в patternProperties.
        """
        return True
    
    def get_pattern_regex(self) -> str:
        """Возвращает regex для patternProperties."""
        if self.pattern:
            return self.pattern.pattern.strip('^$')
        return ".*"
