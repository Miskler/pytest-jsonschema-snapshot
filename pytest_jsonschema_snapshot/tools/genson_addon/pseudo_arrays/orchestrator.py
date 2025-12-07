from typing import Dict, Any, Set, Optional, Tuple
from .detectors import (
    UUIDKeyDetector, ISODateTimeDetector, ISOCodeDetector,
    HexKeyDetector, SingleLetterDetector, NegativeNumericDetector,
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
            SingleLetterDetector(),
            NegativeNumericDetector(),
            NumericStringDetector()
        ]
        # Сортируем по приоритету (высокий приоритет первый)
        self.detectors.sort(key=lambda d: d.PRIORITY, reverse=True)
    
    def detect_pattern(self, keys: Set[str], exclude_patterns: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Определяет паттерн ключей.
        Возвращает None, если не найден подходящий паттерн.
        
        Args:
            keys: Множество ключей для проверки
            exclude_patterns: Имена паттернов, которые следует исключить из проверки
        """
        pattern_info, _ = self.detect_pattern_with_rejects(keys, exclude_patterns)
        return pattern_info
    
    def detect_pattern_with_rejects(self, keys: Set[str], exclude_patterns: Optional[Set[str]] = None) -> Tuple[Optional[Dict[str, Any]], Set[str]]:
        """
        Определяет паттерн ключей и возвращает отвергнутые паттерны.
        
        Args:
            keys: Множество ключей для проверки
            exclude_patterns: Имена паттернов, которые следует исключить из проверки
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Set[str]]: (паттерн-инфо, множество отвергнутых паттернов)
        """
        # Минимум 2 ключа для patternProperties если до этого таковой обработки не было
        if len(keys) < 2 and exclude_patterns is None:
            return None, set()
        
        # Убираем пустые ключи
        non_empty_keys = {k for k in keys if k is not None and k != ""}
        
        if len(non_empty_keys) < 3:
            return None, set()
        
        rejected_patterns = set()
        found_pattern = None
        
        # Для каждого детектора проверяем, подходят ли ему все ключи
        for detector in self.detectors:
            # Пропускаем исключенные паттерны
            str_detector_pattern = str(detector.pattern.pattern)
            if exclude_patterns and str_detector_pattern in exclude_patterns:
                rejected_patterns.add(str_detector_pattern)
                continue
                
            if all(detector.matches(key) for key in non_empty_keys):
                # Проверяем, нужно ли преобразовывать
                if detector.should_convert(non_empty_keys):
                    # Если уже нашли паттерн, выбираем тот, что имеет более высокий приоритет
                    if not found_pattern or detector.PRIORITY > found_pattern['detector'].PRIORITY:
                        found_pattern = {
                            'detector': detector,
                            'pattern_regex': detector.get_pattern_regex(),
                            'name': detector.name,
                            'comment': detector.get_comment()
                        }
                else:
                    # Детектор нашел, но не должен конвертировать
                    rejected_patterns.add(str_detector_pattern)
            else:
                # Детектор не подошел
                rejected_patterns.add(str_detector_pattern)
        
        return found_pattern, rejected_patterns