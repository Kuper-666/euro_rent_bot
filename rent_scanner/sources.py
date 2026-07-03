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
    Source("@mieten_berlin", "Mieten Berlin", "Группа аренды Берлин"),
    Source("@berlin_rentals", "Berlin Rentals", "Свежие объявления в Берлине"),
    Source("@wohnung_berlin", "Wohnung Berlin", "Квартиры Берлин"),
    Source("@immo_deals_berlin", "Immo Deals Berlin", "Выгодные предложения Берлин"),
    Source("@berlin_expats_apartments", "Berlin Expats Apartments", "Для экспатов"),
    Source("@munich_rentals", "Munich Rentals", "Аренда Мюнхен"),
    Source("@russian_berlin_rent", "Русские в Берлине — Аренда", "Русскоязычные объявления"),
    Source("@expats_germany_rent", "Expats Germany Rent", "Аренда по всей Германии"),
]

def enabled_sources() -> list[Source]:
    return [source for source in SOURCES if source.enabled]
