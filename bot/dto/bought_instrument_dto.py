from dataclasses import dataclass


@dataclass
class BoughtInstrumentDto:
    figi: str = '',
    ticker: str = '',
    quantity: int = 0
