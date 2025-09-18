import random
from typing import TypedDict

BIBLE: str = "bible"
POSTFIX: str = "_text"

books = [
    ("Genesis", "GEN", 50, 1),
    ("Exodus", "EXO", 40, 2),
    ("Leviticus", "LEV", 27, 3),
    ("Numbers", "NUM", 36, 4),
    ("Deuteronomy", "DEU", 34, 5),
    ("Joshua", "JOS", 24, 6),
    ("Judges", "JDG", 21, 7),
    ("Ruth", "RUT", 4, 8),
    ("1 Samuel", "1SA", 31, 9),
    ("2 Samuel", "2SA", 24, 10),
    ("1 Kings", "1KI", 22, 11),
    ("2 Kings", "2KI", 25, 12),
    ("1 Chronicles", "1CH", 29, 13),
    ("2 Chronicles", "2CH", 36, 14),
    ("Ezra", "EZR", 10, 15),
    ("Nehemiah", "NEH", 13, 16),
    ("Esther", "EST", 10, 17),
    ("Job", "JOB", 42, 18),
    ("Psalms", "PSA", 150, 19),
    ("Proverbs", "PRO", 31, 20),
    ("Ecclesiastes", "ECC", 12, 21),
    ("Song of Solomon", "SNG", 8, 22),
    ("Isaiah", "ISA", 66, 23),
    ("Jeremiah", "JER", 52, 24),
    ("Lamentations", "LAM", 5, 25),
    ("Ezekiel", "EZK", 48, 26),
    ("Daniel", "DAN", 12, 27),
    ("Hosea", "HOS", 14, 28),
    ("Joel", "JOL", 3, 29),
    ("Amos", "AMO", 9, 30),
    ("Obadiah", "OBA", 1, 31),
    ("Jonah", "JON", 4, 32),
    ("Micah", "MIC", 7, 33),
    ("Nahum", "NAM", 3, 34),
    ("Habakkuk", "HAB", 3, 35),
    ("Zephaniah", "ZEP", 3, 36),
    ("Haggai", "HAG", 2, 37),
    ("Zechariah", "ZEC", 14, 38),
    ("Malachi", "MAL", 4, 39),
    ("Matthew", "MAT", 28, 40),
    ("Mark", "MRK", 16, 41),
    ("Luke", "LUK", 24, 42),
    ("John", "JHN", 21, 43),
    ("Acts", "ACT", 28, 44),
    ("Romans", "ROM", 16, 45),
    ("1 Corinthians", "1CO", 16, 46),
    ("2 Corinthians", "2CO", 13, 47),
    ("Galatians", "GAL", 6, 48),
    ("Ephesians", "EPH", 6, 49),
    ("Philippians", "PHP", 4, 50),
    ("Colossians", "COL", 4, 51),
    ("1 Thessalonians", "1TH", 5, 52),
    ("2 Thessalonians", "2TH", 3, 53),
    ("1 Timothy", "1TI", 6, 54),
    ("2 Timothy", "2TI", 4, 55),
    ("Titus", "TIT", 3, 56),
    ("Philemon", "PHM", 1, 57),
    ("Hebrews", "HEB", 13, 58),
    ("James", "JAS", 5, 59),
    ("1 Peter", "1PE", 5, 60),
    ("2 Peter", "2PE", 3, 61),
    ("1 John", "1JN", 5, 62),
    ("2 John", "2JN", 1, 63),
    ("3 John", "3JN", 1, 64),
    ("Jude", "JUD", 1, 65),
    ("Revelation", "REV", 22, 66),

]



class VersionInfo(TypedDict):
    text: str
    suffix: str
    id: int
    language: str
    name: str
    file: str
    apocrypha: bool

BIBLE = "bible"
# Now, define each dictionary using the VersionInfo type
ABK: VersionInfo = {
    'text': "abk",
    "suffix": "ABK",
    'id': 1079,
    "language": "Cornish",
    "name": "An Bibel Kernewek 20234 (Kernewek Kemmyn)",
    "file": f'{BIBLE}_abk.txt',
    "apocrypha": True,
}
BCNDA: VersionInfo = {
    'text': "bcnda",
    "suffix": "BCNDA",
    'id': 4114,
    "language": "Welsh",
    "name": "Beibl Cymraeg Newydd Diwygiedig yn cynnwys yr Apocryffa 2008",
    "file": f'{BIBLE}_bcnda.txt',
    "apocrypha": False,
}
CPDV: VersionInfo = {
    'text': "cpdv",
    'suffix': "CPDV",
    'id': 42,
    "language": "English",
    "name": "Catholic Public Domain Version",
    "file": f'{BIBLE}_cpdv.txt',
    "apocrypha": True,
}
KOAD21: VersionInfo = {
    'text': "koad21",
    "suffix": "KOAD21",
    'id': 1231,
    "language": "Breton",
    "name": "Bibl Koad 21",
    "file": f'{BIBLE}_koad21.txt',
    "apocrypha": True,
}
NIV: VersionInfo = {
    'text': "niv",
    'suffix': "NIV",
    'id': 111,
    "language": "English",
    "name": "New International Version",
    "file": f'{BIBLE}_niv.txt',
    "apocrypha": False,
}

def get_random_version() -> VersionInfo:
    """Selects and returns a random version from the VERSIONS list."""
    return random.choice(VERSIONS)

VERSIONS = [
    KOAD21,
    BCNDA,
    ABK,
    NIV
]