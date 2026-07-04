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
    Source("@wohnung_berlin", "Wohnung Berlin", "Персидский канал аренды Берлин"),
    Source("@russians_in_berlin", "Русские в Берлине", "Русскоязычные объявления Берлин"),
    Source("@immomessengerberlin", "Berlin Immobilien", "Немецкий канал аренды Берлин"),
    Source("@wohnung_hamburg", "Wohnung Hamburg", "Немецкий канал аренды Гамбург"),
    Source("@muenchen_wohnungen", "München Wohnungen", "Немецкий канал аренды Мюнхен"),
    # AT Austria
    Source("@wien_wohnung", "Квартиры в Вене", "Русскоязычные объявления Вена"),
    # CZ Czech
    Source("@pronajem_praha", "Оренда Прага", "Украинские объявления Прага"),
    Source("@arendaprahacesko", "Аренда Прага", "Русскоязычные аренды Прага"),
    Source("@pronajem_bydleni_praha", "Аренда жилья Прага", "Украинские аренды Прага"),
    Source("@praguelifeestate", "Pronajem Praha", "Чешские аренды Прага"),
    # PL Poland
    Source("@warszawa_mieszkania", "Аренда Варшава", "Русскоязычные аренды Варшава"),
    Source("@mieszkania_wynajem_warszawa", "Mieszkania wynajem Warszawa", "Польские аренды Варшава"),
    Source("@mieszkania_warszawa_creative", "Mieszkania Warszawa Creative", "Польские аренды Варшава"),
    Source("@moreEtate", "more Estate Warszawa", "Аренды Варшава"),
    Source("@rentapartaments_waw", "Rent Apartments Warszawa", "Аренды Варшава"),
    Source("@krakow_mieszkania", "Mieszkania Kraków", "Польские аренды Краков"),
    # IT Italy
    Source("@appartamentiaffittoMilano", "Affitto Milano", "Итальянские аренды Милан"),
    Source("@appartamentiRoma_SBG", "Affitto Roma", "Итальянские аренды Рим"),
    Source("@romaaffitto", "Roma Affitto", "Итальянские аренды Рим"),
    Source("@affittostanzeeappartamentiaroma", "Affitto Roma Stanze", "Комнаты в Риме"),
    Source("@milanhousesrent", "Milano Affitto", "Итальянские аренды Милан"),
    Source("@appartamenti_automatico", "Appartamenti Milano", "Автопостинг Милан"),
    Source("@camereeappartamentiamilano", "Affitto Milano Stanze", "Комнаты в Милане"),
    # ES Spain
    Source("@realestateabaru", "Недвижимость Барселона", "Аренды Барселона"),
    Source("@alquilerpiso_madrid", "Alquiler Madrid", "Аренды Мадрид"),
    # PT Portugal
    Source("@lisbonapartments", "Lisbon Apartments", "Аренды Лиссабон"),
    Source("@portoapartments", "Porto Apartments", "Аренды Порту"),
    Source("@arrend_lisboa", "Arrendamento Lisboa", "Португальские аренды Лиссабон"),
    # NL Netherlands
    Source("@amsterdamapartments", "Amsterdam Apartments", "Аренды Амстердам"),
    Source("@woning_amsterdam", "Woning Amsterdam", "Голландские аренды Амстердам"),
    # FR France
    Source("@paris_appartements", "Appartements Paris", "Аренды Париж"),
    Source("@lyon_appartements", "Appartements Lyon", "Аренды Лион"),
    # IE Ireland
    Source("@dublin_rentals", "Dublin Rentals", "Аренды Дублин"),
    # HU Hungary
    Source("@budapest_apartments", "Budapest Apartments", "Аренды Будапешт"),
    # GR Greece
    Source("@athens_rentals", "Athens Rentals", "Аренды Афины"),
    # UK United Kingdom
    Source("@SpacesLondon", "London Rentals", "Лондон аренды (рус)"),
    Source("@LondonRentHub", "London Rentals & Rooms", "Лондон аренды"),
    Source("@manchester_rentals", "Manchester Rentals", "Аренды Манчестер"),
]

def enabled_sources() -> list[Source]:
    return [source for source in SOURCES if source.enabled]
