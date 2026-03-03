from rapidfuzz import process, fuzz
from typing import List, Optional, Dict
import re

class NormalizationEngine:
    def __init__(self, db_session=None):
        self.db_session = db_session
        # Expanded multipliers for national data standards
        self.unit_multipliers = {
            "KG": 1.0,
            "KILOGRAM": 1.0,
            "QUINTAL": 100.0,
            "TON": 1000.0,
            "TONNE": 1000.0,
            "M. TON": 1000.0,
            "BAG": 50.0, # Approximate standard for grains
            "GRAM": 0.001,
        }

    def normalize_unit(self, unit_name: str) -> str:
        unit_name = unit_name.upper().strip()
        if "QUINTAL" in unit_name: return "QUINTAL"
        if any(k in unit_name for k in ["KG", "KILO"]): return "KG"
        if any(k in unit_name for k in ["TON", "TONNE"]): return "TON"
        if "BAG" in unit_name: return "BAG"
        return unit_name

    def calculate_price_per_kg(self, price: float, unit: str) -> float:
        multiplier = self.unit_multipliers.get(unit, 1.0)
        return price / multiplier if multiplier > 0 else price

    def fuzzy_match(self, input_name: str, master_list: List[Dict], threshold: int = 80) -> Optional[int]:
        """
        Generic fuzzy matching for commodities, varieties, or markets.
        master_list: List of dicts with {'id': id, 'name': name, 'aliases': []}
        """
        if not input_name or not master_list:
            return None
            
        choices = {}
        for item in master_list:
            choices[item['name']] = item['id']
            for alias in item.get('aliases', []):
                choices[alias] = item['id']
            
        match = process.extractOne(input_name, list(choices.keys()), scorer=fuzz.WRatio)
        if match and match[1] >= threshold:
            return choices[match[0]]
        return None

    def clean_price_string(self, price_str: str) -> float:
        try:
            # Remove any non-numeric characters except decimal point
            clean_str = re.sub(r'[^\d.]', '', str(price_str))
            return float(clean_str)
        except (ValueError, TypeError):
            return 0.0
