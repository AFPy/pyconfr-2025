import json
from datetime import date, datetime, time
from pathlib import Path
from sys import exit
from urllib.request import Request, urlopen

# Constants, should be changed each year.

URL_BASE = "https://cfp.pycon.fr/api/events/pyconfr-2025/"
TALKS_URL = f"{URL_BASE}submissions/?limit=1000&questions=all"
ROOMS_URL = f"{URL_BASE}rooms/?limit=1000"
TOKEN_FILE = Path("token.key")
OUTPUT = Path("schedule.json")
if TOKEN_FILE.is_file():
    TOKEN = TOKEN_FILE.read_text()
else:
    print(f"ERROR: Please put your Pretalx token in the {TOKEN_FILE} file.")
    exit()

SPRINT_DAYS = (
    date(year=2025, month=10, day=30),
    date(year=2025, month=10, day=31),
)
CONFERENCE_DAYS = (
    date(year=2025, month=11, day=1),
    date(year=2025, month=11, day=2),
)
DAY_START_TIME = time(hour=8, minute=30)
DAY_STOP_TIME = time(hour=18, minute=0)
SLOT_MINUTES = 30

EXTRA = {
    "2025-11-01": {
        "510": {
            "id": "saturday-breakfast",
            "title": {
                "en": "Breakfast",
                "fr": "Petit-déjeuner",
            }
        },
        "750": {
            "id": "saturday-lunch",
            "title": {
                "en": "Lunch",
                "fr": "Déjeuner",
            }
        },
        "960": {
            "id": "saturday-snack",
            "title": {
                "en": "Snack Time",
                "fr": "Goûter",
            }
        },
    },
    "2025-11-02": {
        "510": {
            "id": "sunday-breakfast",
            "title": {
                "en": "Breakfast",
                "fr": "Petit-déjeuner",
            }
        },
        "750": {
            "id": "sunday-lunch",
            "title": {
                "en": "Lunch",
                "fr": "Déjeuner",
            }
        },
    },
}


# Define some util functions.

def to_minutes(time):
    """Get number of minutes in datetime.time."""
    return time.hour * 60 + time.minute

def to_time(minutes):
    """Generate datetime.time containing given minutes."""
    return time(hour=minutes//60, minute=minutes%60)

def clean_talk(talk):
    """Remove non-public data from talks"""
    for speaker in talk["speakers"]:
        del speaker["email"]
    for key in ("do_not_record", "notes", "internal_notes"):
        del talk[key]


# Check constants consistency.

assert DAY_START_TIME < DAY_STOP_TIME
assert to_minutes(DAY_START_TIME) % SLOT_MINUTES == 0
assert to_minutes(DAY_STOP_TIME) % SLOT_MINUTES == 0


# Download talks and rooms from API.

print("Downloading talks")
request = Request(TALKS_URL, headers={"Authorization": f"Token {TOKEN}"})
response = urlopen(request)
talks = tuple(talk for talk in json.loads(response.read())["results"] if talk["slot"])

print("Downloading rooms")
request = Request(ROOMS_URL, headers={"Authorization": f"Token {TOKEN}"})
response = urlopen(request)
rooms = sorted(json.loads(response.read())["results"], key=lambda room: room["position"])
rooms_dict = {room["id"]: room for room in rooms}


# Build table for conferences.

print("Generating schedule")
slots = range(to_minutes(DAY_START_TIME), to_minutes(DAY_STOP_TIME), SLOT_MINUTES)
hours = [to_time(minutes) for minutes in slots]
schedule = {day.isoformat(): {to_minutes(hour): {} for hour in hours} for day in CONFERENCE_DAYS}
sprints = {day.isoformat(): {to_minutes(hour): {} for hour in hours} for day in SPRINT_DAYS}
for talk in talks:
    slot = talk["slot"]
    # We assume that talks and schedule share the same timezone.
    if not slot["start"]:
        continue
    start = datetime.fromisoformat(slot["start"])
    end = datetime.fromisoformat(slot["end"])
    clean_talk(talk)
    slot_start_minutes = to_minutes(start) // SLOT_MINUTES * SLOT_MINUTES
    slot_start = to_time(slot_start_minutes)
    if start.date() in CONFERENCE_DAYS:
        schedule[start.date().isoformat()][to_minutes(slot_start)][slot["room_id"]] = talk
        rooms_dict[slot["room_id"]]["in_conferences"] = True
    elif start.date() in SPRINT_DAYS:
        sprints[start.date().isoformat()][to_minutes(slot_start)][slot["room_id"]] = talk
        rooms_dict[slot["room_id"]]["in_sprints"] = True
    else:
        print("Wrong date for talk:", talk)

print(f"Writing schedule to {OUTPUT}")
OUTPUT.write_text(json.dumps({
    "schedule": schedule,
    "sprints": sprints,
    "rooms": rooms,
    "extra": EXTRA,
    "speakers": {
        speaker["code"]: speaker
        for hours in schedule.values()
        for rooms in hours.values()
        for room in rooms.values()
        for speaker in room["speakers"]
    },
}).replace('http://cfp.pycon.fr/', 'https://cfp.pycon.fr/'))
