# [file name]: pseudo_array_converter.py
from __future__ import annotations

from genson import SchemaBuilder
from ..string import CustomString
from ..object import PatternObjectStrategy

class PseudoArrayConverter(SchemaBuilder):
    """
    Исправленный конвертер с учетом объединения нескольких схем.
    """
    
    MAX_DEPTH = 1000
    EXTRA_STRATEGIES = (CustomString, PatternObjectStrategy)
