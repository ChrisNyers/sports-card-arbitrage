"""A static catalog of plausible sports cards used to generate mock market data.

card_id is assigned as the 1-based index into CARDS at import time (see get_cards()).
"""
from __future__ import annotations

from cardarb.db.models import Card

_RAW_CARDS = [
    # (player_name, year, set_name, card_number, variant, sport, grade)
    ("Victor Wembanyama", 2023, "Panini Prizm", "1", "Silver", "basketball", "PSA 10"),
    ("Victor Wembanyama", 2023, "Panini Prizm", "1", "Base", "basketball", "PSA 9"),
    ("Caitlin Clark", 2024, "Panini Prizm WNBA", "1", "Base", "basketball", "PSA 10"),
    ("LeBron James", 2003, "Topps Chrome", "111", "Base", "basketball", "PSA 9"),
    ("Michael Jordan", 1986, "Fleer", "57", "Base", "basketball", "PSA 8"),
    ("Luka Doncic", 2018, "Panini Prizm", "280", "Silver", "basketball", "PSA 10"),
    ("Ja Morant", 2019, "Panini Prizm", "249", "Base", "basketball", "PSA 10"),
    ("Anthony Edwards", 2020, "Panini Prizm", "258", "Base", "basketball", "PSA 10"),
    ("Patrick Mahomes", 2017, "Panini Contenders", "301", "Rookie Ticket Auto", "football", "PSA 9"),
    ("Josh Allen", 2018, "Panini Prizm", "255", "Base", "football", "PSA 10"),
    ("Justin Jefferson", 2020, "Panini Prizm", "398", "Base", "football", "PSA 10"),
    ("CJ Stroud", 2023, "Panini Prizm", "310", "Base", "football", "PSA 10"),
    ("Caleb Williams", 2024, "Panini Prizm", "301", "Base", "football", "PSA 10"),
    ("Tom Brady", 2000, "Playoff Contenders", "144", "Rookie Ticket Auto", "football", "PSA 8"),
    ("Ronald Acuna Jr.", 2018, "Topps Chrome", "175", "Base", "baseball", "PSA 10"),
    ("Shohei Ohtani", 2018, "Topps Chrome", "150", "Base", "baseball", "PSA 10"),
    ("Julio Rodriguez", 2022, "Topps Chrome", "98", "Base", "baseball", "PSA 10"),
    ("Mike Trout", 2011, "Topps Update", "US175", "Base", "baseball", "PSA 9"),
    ("Bobby Witt Jr.", 2020, "Bowman Chrome", "BCP-49", "Base", "baseball", "PSA 10"),
    ("Wander Franco", 2021, "Bowman Chrome", "BCP-1", "Base", "baseball", "PSA 9"),
    ("Connor Bedard", 2023, "Upper Deck Young Guns", "451", "Base", "hockey", "PSA 10"),
    ("Connor McDavid", 2015, "Upper Deck Young Guns", "201", "Base", "hockey", "PSA 9"),
    ("Auston Matthews", 2016, "Upper Deck Young Guns", "201", "Base", "hockey", "PSA 10"),
    ("Sidney Crosby", 2005, "Upper Deck Young Guns", "201", "Base", "hockey", "PSA 8"),
    ("Wayne Gretzky", 1979, "O-Pee-Chee", "18", "Base", "hockey", "PSA 7"),
    ("Kobe Bryant", 1996, "Topps Chrome", "138", "Refractor", "basketball", "PSA 9"),
    ("Stephen Curry", 2009, "Topps", "321", "Base", "basketball", "PSA 9"),
    ("Zion Williamson", 2019, "Panini Prizm", "248", "Base", "basketball", "PSA 10"),
    ("Paolo Banchero", 2022, "Panini Prizm", "279", "Base", "basketball", "PSA 10"),
    ("Chet Holmgren", 2022, "Panini Prizm", "292", "Base", "basketball", "PSA 10"),
    ("Deion Sanders", 1989, "Score", "270", "Base", "football", "PSA 9"),
    ("Jayden Daniels", 2024, "Panini Prizm", "309", "Base", "football", "PSA 10"),
    ("Marvin Harrison Jr.", 2024, "Panini Prizm", "304", "Base", "football", "PSA 10"),
    ("Aaron Judge", 2017, "Topps Chrome", "169", "Base", "baseball", "PSA 10"),
    ("Fernando Tatis Jr.", 2019, "Topps Chrome", "203", "Base", "baseball", "PSA 10"),
    ("Elly De La Cruz", 2023, "Bowman Chrome", "BCP-27", "Base", "baseball", "PSA 10"),
    ("Gunnar Henderson", 2022, "Bowman Chrome", "BCP-114", "Base", "baseball", "PSA 10"),
    ("Macklin Celebrini", 2024, "Upper Deck Young Guns", "201", "Base", "hockey", "PSA 10"),
    ("Nikita Kucherov", 2013, "Upper Deck Young Guns", "204", "Base", "hockey", "PSA 9"),
    ("Cale Makar", 2019, "Upper Deck Young Guns", "224", "Base", "hockey", "PSA 10"),
    ("Giannis Antetokounmpo", 2013, "Panini Prizm", "290", "Base", "basketball", "PSA 9"),
    ("Nikola Jokic", 2015, "Panini Prizm", "292", "Base", "basketball", "PSA 8"),
    ("Joe Burrow", 2020, "Panini Prizm", "302", "Base", "football", "PSA 10"),
    ("Bryce Young", 2023, "Panini Prizm", "302", "Base", "football", "PSA 9"),
    ("Juan Soto", 2018, "Topps Chrome", "160", "Base", "baseball", "PSA 10"),
    ("Corbin Carroll", 2022, "Bowman Chrome", "BCP-100", "Base", "baseball", "PSA 10"),
]


def get_cards() -> list[Card]:
    return [
        Card(
            card_id=idx,
            player_name=player_name,
            year=year,
            set_name=set_name,
            card_number=card_number,
            variant=variant,
            sport=sport,
            grade=grade,
        )
        for idx, (player_name, year, set_name, card_number, variant, sport, grade) in enumerate(
            _RAW_CARDS, start=1
        )
    ]
