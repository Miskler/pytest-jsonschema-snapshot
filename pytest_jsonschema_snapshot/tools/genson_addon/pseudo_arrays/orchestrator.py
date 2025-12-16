# [file name]: orchestrator.py
from typing import Dict, Any, Set, Optional, Tuple, List
import re
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
        Определяет паттерн для одного набора ключей.
        """
        pattern_info, _ = self.detect_pattern_with_rejects(keys, exclude_patterns)
        return pattern_info
    
    def detect_pattern_with_rejects(self, keys: Set[str], exclude_patterns: Optional[Set[str]] = None) -> Tuple[Optional[Dict[str, Any]], Set[str]]:
        """
        Определяет паттерн ключей и возвращает отвергнутые паттерны.
        """
        # Минимум 3 ключа для patternProperties
        if len(keys) < 3:
            return None, set()
        
        # Убираем пустые ключи
        non_empty_keys = {k for k in keys if k is not None and k != ""}
        
        if len(non_empty_keys) < 3:
            return None, set()
        
        rejected_patterns = set()
        found_pattern = None
        
        for detector in self.detectors:
            str_detector_pattern = f"^{detector.get_pattern_regex()}$"
            if exclude_patterns and str_detector_pattern in exclude_patterns:
                rejected_patterns.add(str_detector_pattern)
                continue
                
            if all(detector.matches(key) for key in non_empty_keys):
                if detector.should_convert(non_empty_keys):
                    if not found_pattern or detector.PRIORITY > found_pattern['detector'].PRIORITY:
                        found_pattern = {
                            'detector': detector,
                            'pattern_regex': detector.get_pattern_regex(),
                            'name': type(detector).__name__,
                            'comment': detector.get_comment()
                        }
                # Не добавляем в rejected, если should_convert=False - это позволяет использовать superset в merging
            else:
                rejected_patterns.add(str_detector_pattern)
        
        return found_pattern, rejected_patterns
    
    def find_best_pattern_for_schemas(self, pattern_schemas: List[Dict[str, Any]], blacklisted_patterns: Set[str] = None) -> Optional[Dict[str, Any]]:
        """
        Находит наилучший паттерн для объединения нескольких схем с patternProperties.
        """
        if not pattern_schemas:
            return None
            
        # Извлекаем паттерны из всех схем
        all_patterns = []
        for schema in pattern_schemas:
            if "propertyNames" in schema and "pattern" in schema["propertyNames"]:
                pattern = schema["propertyNames"]["pattern"]
                # Убираем ^ и $ если есть
                if pattern.startswith('^') and pattern.endswith('$'):
                    pattern = pattern[1:-1]
                all_patterns.append(pattern)
        
        if not all_patterns:
            return None
            
        # Находим детекторы для input паттернов
        input_detectors = []
        for p in all_patterns:
            d = self.get_detector_for_pattern(p)
            if d:
                input_detectors.append(d)
            else:
                return None  # Неизвестный паттерн
        
        # Собираем все примеры из input детекторов
        all_examples = set()
        for d in input_detectors:
            all_examples.update(d.examples)
        
        # Находим лучший детектор, который покрывает все примеры
        best_detector = None
        for candidate in self.detectors:
            cand_full = f"^{candidate.get_pattern_regex()}$"
            if blacklisted_patterns and cand_full in blacklisted_patterns:
                continue
                
            if all(candidate.matches(ex) for ex in all_examples):
                if candidate.should_convert(all_examples):
                    if best_detector is None or candidate.PRIORITY > best_detector.PRIORITY:
                        best_detector = candidate
        
        if best_detector:
            return {
                'detector': best_detector,
                'pattern_regex': best_detector.get_pattern_regex(),
                'name': type(best_detector).__name__,
                'comment': best_detector.get_comment()
            }
        
        return None
    
    def detect_pattern_from_schema(self, schema: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает паттерн из схемы, если это patternProperties.
        """
        if "propertyNames" in schema and "pattern" in schema["propertyNames"]:
            pattern = schema["propertyNames"]["pattern"]
            if pattern.startswith('^') and pattern.endswith('$'):
                return pattern[1:-1]
            return pattern
        return None
    
    def get_detector_for_pattern(self, pattern_regex: str):
        """
        Находит детектор для заданного паттерна.
        """
        for detector in self.detectors:
            if detector.get_pattern_regex() == pattern_regex:
                return detector
        return None