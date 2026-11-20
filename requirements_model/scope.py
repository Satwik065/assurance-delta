"""A strictly closed grammar for evaluating WAIVE scope predicates.
We never use eval(). We parse the string manually.
"""
from __future__ import annotations
import re
from typing import Any

class ScopePredicate:
    """Represents a predicate like: class == 'BULK' and load <= 2.0"""
    def __init__(self, text: str):
        self.text = text.strip()
        self.clauses = self._parse(self.text)

    def _parse(self, text: str) -> list[tuple[str, str, Any]]:
        # Split by "and" (e.g., "class == 'BULK' and load <= 2.0")
        parts = text.split(" and ")
        clauses = []
        for part in parts:
            part = part.strip()
            # Match: variable operator value (e.g., class == 'BULK')
            match = re.match(r"^(\w+)\s*(==|<=|>=|<|>)\s*(.+)$", part)
            if not match:
                raise ValueError(f"Invalid scope syntax: {part}")
            
            var, op, val_str = match.groups()
            val_str = val_str.strip().strip("'\"") # remove quotes if present
            
            # Try to parse val as a float if possible
            try:
                val: Any = float(val_str)
            except ValueError:
                val = val_str
                
            clauses.append((var, op, val))
        return clauses

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluates the predicate against a context like {'class': 'BULK', 'load': 1.5}"""
        for var, op, val in self.clauses:
            if var not in context:
                return False # Variable missing -> fail safe
            
            ctx_val = context[var]
            
            if op == "==":
                if ctx_val != val: return False
            elif op == "<=":
                if not (ctx_val <= val): return False
            elif op == ">=":
                if not (ctx_val >= val): return False
            elif op == "<":
                if not (ctx_val < val): return False
            elif op == ">":
                if not (ctx_val > val): return False
                
        return True
