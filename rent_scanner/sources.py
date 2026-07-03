from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Source:
    handle: str
    title: str
    reason: str
    enabled: bool = True

    @property
    def username(self) -> str:
        return self.handle.removeprefix("@")

    @property
    def telegram_url(self) -> str:
        return f"https://t.me/{self.username}"

SOURCES: list[Source] = [
    # DE Germany
    Source("@wohnung_berlin", "Wohnung Berlin", "Крупный канал с квартирами в Берлине"),
    Source("@russians_in_berlin", "Русские в Берлине", "Много объявлений от русскоязычных"),
    # AT Austria
    Source("@wien_wohnung", "Квартиры в Вене", "Русскоязычные объявления Вена"),
    # CZ Czech
    Source("@pronajem_praha", "Оренда Прага", "Украинские объявления Прага"),
]

def enabled_sources() -> list[Source]:
    return [source for source in SOURCES if source.enabled]
