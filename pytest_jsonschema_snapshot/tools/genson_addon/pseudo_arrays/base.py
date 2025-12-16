from abc import ABC
from typing import Optional, Set, List
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
    
    def get_examples(self) -> List[str]:
        """Возвращает примеры ключей для этого паттерна."""
        return self.examples if hasattr(self, 'examples') else []
    
    def pattern_matches_examples(self, other_detector: 'KeyPatternDetector') -> bool:
        """Проверяет, подходят ли все примеры другого детектора под этот паттерн."""
        for example in other_detector.get_examples():
            if not self.matches(example):
                return False
        return True

    def covers_pattern(self, other_pattern: str) -> bool:
        """
        Проверяет, покрывает ли этот паттерн другой паттерн.
        Возвращает True, если все примеры другого паттерна подходят под этот паттерн.
        """
        if not hasattr(self, 'examples') or not hasattr(other_pattern, 'examples'):
            return False
            
        # Если у нас нет примеров для сравнения, используем логическое включение
        # Проверяем, соответствует ли паттерн другого детектора нашему паттерну
        try:
            other_regex = re.compile(other_pattern)
            # Проверяем несколько тестовых значений
            test_values = self.examples if hasattr(self, 'examples') else []
            return all(other_regex.match(str(val)) for val in test_values)
        except:
            return False

    def covers(self, other_detector: 'KeyPatternDetector') -> bool:
        """
        Проверяет, покрывает ли этот детектор другой детектор.
        Детектор A покрывает детектор B, если все ключи, которые соответствуют B,
        также соответствуют A.
        """
        # Проверяем по примерам другого детектора
        if hasattr(other_detector, 'examples'):
            for example in other_detector.examples:
                if not self.matches(example):
                    return False
            return True
        
        # Если примеров нет, используем эвристику на основе регулярных выражений
        # Простая проверка: если паттерн B является более строгим подмножеством паттерна A
        # Например, ^\d+$ покрывается ^-?\d+$
        a_pattern = str(self.pattern.pattern)
        b_pattern = str(other_detector.pattern.pattern)
        
        # Простая эвристика: если b_pattern более специфичен
        if b_pattern.startswith(a_pattern.replace('?', '')):
            return True
            
        # Проверяем конкретные случаи
        if a_pattern == r'^-?\d+$' and b_pattern == r'^\d+$':
            return True
            
        return False
