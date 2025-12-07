# src/jsonschema_infer/key_patterns/orchestrator.py
from typing import Dict, Any, Set, List, Optional
from .detectors import (
    UUIDKeyDetector, ISODateTimeDetector, ISOCodeDetector,
    HexKeyDetector, AlphabeticKeyDetector, NegativeNumericDetector,
    NumericStringDetector
)


class KeyPatternOrchestrator:
    """Оркестратор детекторов паттернов ключей."""
    
    def __init__(self):
        # Инициализируем детекторы в порядке приоритета
        self.detectors = [
            UUIDKeyDetector(),
            ISODateTimeDetector(),
            ISOCodeDetector(),
            HexKeyDetector(),
            AlphabeticKeyDetector(),
            NegativeNumericDetector(),
            NumericStringDetector(),
        ]
        # Сортируем по приоритету (высокий приоритет первый)
        self.detectors.sort(key=lambda d: d.PRIORITY, reverse=True)
    
    def detect_pattern(self, keys: Set[str]) -> Optional[Dict[str, Any]]:
        """
        Определяет паттерн ключей.
        Возвращает None, если не найден подходящий паттерн.
        """
        if len(keys) < 3:  # Минимум 3 ключа для patternProperties
            return None
        
        # Убираем пустые ключи
        non_empty_keys = {k for k in keys if k is not None and k != ""}
        
        if len(non_empty_keys) < 3:
            return None
        
        # Для каждого детектора проверяем, подходят ли ему все ключи
        for detector in self.detectors:
            if all(detector.matches(key) for key in non_empty_keys):
                # Проверяем, нужно ли преобразовывать
                if detector.should_convert(non_empty_keys):
                    return {
                        'detector': detector,
                        'pattern_regex': detector.get_pattern_regex(),
                        'name': detector.name,
                    }
        
        return None