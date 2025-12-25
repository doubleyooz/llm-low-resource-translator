import random
from typing import List, TypedDict

BIBLE: str = "bible"
POSTFIX: str = "_text"

FASTER = "faster"
DEFAULT = "default"
SLOWER = "slower"

class BookInfo(TypedDict):
    name: str
    abbr: str
    chapters: int
    id: str
    
# Hardcoded book data: (name, abbr, chapters, id)
# Book IDs are sequential starting from 1 (Genesis=1, etc.)

books: List[BookInfo] = [
    {"name": "Genesis",         "abbr": "GEN", "chapters": 50, "id": 1},
    {"name": "Exodus",          "abbr": "EXO", "chapters": 40, "id": 2},
    {"name": "Leviticus",       "abbr": "LEV", "chapters": 27, "id": 3},
    {"name": "Numbers",         "abbr": "NUM", "chapters": 36, "id": 4},
    {"name": "Deuteronomy",     "abbr": "DEU", "chapters": 34, "id": 5},
    {"name": "Joshua",          "abbr": "JOS", "chapters": 24, "id": 6},
    {"name": "Judges",          "abbr": "JDG", "chapters": 21, "id": 7},
    {"name": "Ruth",            "abbr": "RUT", "chapters": 4,  "id": 8},
    {"name": "1 Samuel",        "abbr": "1SA", "chapters": 31, "id": 9},
    {"name": "2 Samuel",        "abbr": "2SA", "chapters": 24, "id": 10},
    {"name": "1 Kings",         "abbr": "1KI", "chapters": 22, "id": 11},
    {"name": "2 Kings",         "abbr": "2KI", "chapters": 25, "id": 12},
    {"name": "1 Chronicles",    "abbr": "1CH", "chapters": 29, "id": 13},
    {"name": "2 Chronicles",    "abbr": "2CH", "chapters": 36, "id": 14},
    {"name": "Ezra",            "abbr": "EZR", "chapters": 10, "id": 15},
    {"name": "Nehemiah",        "abbr": "NEH", "chapters": 13, "id": 16},
    {"name": "Esther",          "abbr": "EST", "chapters": 10, "id": 17},
    {"name": "Job",             "abbr": "JOB", "chapters": 42, "id": 18},
    {"name": "Psalms",          "abbr": "PSA", "chapters": 150,"id": 19},
    {"name": "Proverbs",        "abbr": "PRO", "chapters": 31, "id": 20},
    {"name": "Ecclesiastes",    "abbr": "ECC", "chapters": 12, "id": 21},
    {"name": "Song of Solomon", "abbr": "SNG", "chapters": 8,  "id": 22},
    {"name": "Isaiah",          "abbr": "ISA", "chapters": 66, "id": 23},
    {"name": "Jeremiah",        "abbr": "JER", "chapters": 52, "id": 24},
    {"name": "Lamentations",    "abbr": "LAM", "chapters": 5,  "id": 25},
    {"name": "Ezekiel",         "abbr": "EZK", "chapters": 48, "id": 26},
    {"name": "Daniel",          "abbr": "DAN", "chapters": 12, "id": 27},
    {"name": "Hosea",           "abbr": "HOS", "chapters": 14, "id": 28},
    {"name": "Joel",            "abbr": "JOL", "chapters": 3,  "id": 29},
    {"name": "Amos",            "abbr": "AMO", "chapters": 9,  "id": 30},
    {"name": "Obadiah",         "abbr": "OBA", "chapters": 1,  "id": 31},
    {"name": "Jonah",           "abbr": "JON", "chapters": 4,  "id": 32},
    {"name": "Micah",           "abbr": "MIC", "chapters": 7,  "id": 33},
    {"name": "Nahum",           "abbr": "NAM", "chapters": 3,  "id": 34},
    {"name": "Habakkuk",        "abbr": "HAB", "chapters": 3,  "id": 35},
    {"name": "Zephaniah",       "abbr": "ZEP", "chapters": 3,  "id": 36},
    {"name": "Haggai",          "abbr": "HAG", "chapters": 2,  "id": 37},
    {"name": "Zechariah",       "abbr": "ZEC", "chapters": 14, "id": 38},
    {"name": "Malachi",         "abbr": "MAL", "chapters": 4,  "id": 39},

    # Deuterocanonical books (Catholic/Orthodox)
    {"name": "Tobit",           "abbr": "TOB", "chapters": 14, "id": 40},
    {"name": "Judith",          "abbr": "JDT", "chapters": 16, "id": 41},
    {"name": "1 Maccabees",     "abbr": "1MA", "chapters": 16, "id": 42},
    {"name": "2 Maccabees",     "abbr": "2MA", "chapters": 15, "id": 43},
    {"name": "Wisdom",          "abbr": "WIS", "chapters": 19, "id": 44},
    {"name": "Sirach",          "abbr": "SIR", "chapters": 51, "id": 45},
    {"name": "Baruch",          "abbr": "BAR", "chapters": 6,  "id": 46},

    # New Testament
    {"name": "Matthew",         "abbr": "MAT", "chapters": 28, "id": 47},
    {"name": "Mark",            "abbr": "MRK", "chapters": 16, "id": 48},
    {"name": "Luke",            "abbr": "LUK", "chapters": 24, "id": 49},
    {"name": "John",            "abbr": "JHN", "chapters": 21, "id": 50},
    {"name": "Acts",            "abbr": "ACT", "chapters": 28, "id": 51},
    {"name": "Romans",          "abbr": "ROM", "chapters": 16, "id": 52},
    {"name": "1 Corinthians",   "abbr": "1CO", "chapters": 16, "id": 53},
    {"name": "2 Corinthians",   "abbr": "2CO", "chapters": 13, "id": 54},
    {"name": "Galatians",       "abbr": "GAL", "chapters": 6,  "id": 55},
    {"name": "Ephesians",       "abbr": "EPH", "chapters": 6,  "id": 56},
    {"name": "Philippians",     "abbr": "PHP", "chapters": 4,  "id": 57},
    {"name": "Colossians",      "abbr": "COL", "chapters": 4,  "id": 58},
    {"name": "1 Thessalonians", "abbr": "1TH", "chapters": 5,  "id": 59},
    {"name": "2 Thessalonians", "abbr": "2TH", "chapters": 3,  "id": 60},
    {"name": "1 Timothy",       "abbr": "1TI", "chapters": 6,  "id": 61},
    {"name": "2 Timothy",       "abbr": "2TI", "chapters": 4,  "id": 62},
    {"name": "Titus",           "abbr": "TIT", "chapters": 3,  "id": 63},
    {"name": "Philemon",        "abbr": "PHM", "chapters": 1,  "id": 64},
    {"name": "Hebrews",         "abbr": "HEB", "chapters": 13, "id": 65},
    {"name": "James",           "abbr": "JAS", "chapters": 5,  "id": 66},
    {"name": "1 Peter",         "abbr": "1PE", "chapters": 5,  "id": 67},
    {"name": "2 Peter",         "abbr": "2PE", "chapters": 3,  "id": 68},
    {"name": "1 John",          "abbr": "1JN", "chapters": 5,  "id": 69},
    {"name": "2 John",          "abbr": "2JN", "chapters": 1,  "id": 70},
    {"name": "3 John",          "abbr": "3JN", "chapters": 1,  "id": 71},
    {"name": "Jude",            "abbr": "JUD", "chapters": 1,  "id": 72},
    {"name": "Revelation",      "abbr": "REV", "chapters": 22, "id": 73},
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
    'id': 4523,
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

CPDV: VersionInfo = {
    'text': "cpdv",
    'suffix': "CPDV",
    'id': 42,
    "language": "English",
    "name": "Catholic Public Domain Version",
    "file": f'{BIBLE}_cpdv.txt',
    "apocrypha": True,
}

PDV2017: VersionInfo = {
    'text': "pdv2017",
    'suffix': "PDV2017",
    'id': 133,
    "language": "French",
    "name": "Parole de Vie 2017",
    "file": f'{BIBLE}_pdv2017.txt',
    "apocrypha": True,
}

# Mark 4:40-41 are merged into a single verse in BCC1923
BCC1923: VersionInfo = {
    'text': "bcc1923",
    'suffix': "BCC1923",
    'id': 504,
    "language": "French",
    "name": "Bible Catholique Crampon 1923",
    "file": f'{BIBLE}_bcc1923.txt',
    "apocrypha": True,
}


def get_random_version() -> VersionInfo:
    """Selects and returns a random version from the VERSIONS list."""
    return random.choice(VERSIONS)

VERSIONS = [
    KOAD21,
    BCNDA,
    ABK,
    CPDV,
    BCC1923,
]