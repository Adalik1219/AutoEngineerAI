"""Společné chyby kontraktů AutoEngineerAI."""

from __future__ import annotations


class ContractError(ValueError):
    """Chyba kontraktu s cestou k poli a českou zprávou."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path or "$"
        super().__init__(f"{self.path}: {message}")


def format_error(path: str, message: str) -> str:
    """Jednořádkový český popis chyby: `<cesta>: <zpráva>`."""
    return f"{path or '$'}: {message}"
