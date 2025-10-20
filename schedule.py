import json
from datetime import date, datetime, time
from pathlib import Path
from sys import exit
from urllib.request import Request, urlopen

# Constants, should be changed each year.

URL_BASE = "https://cfp.pycon.fr/api/events/pyconfr-2025/"
TALKS_URL = f"{URL_BASE}submissions/?expand=slots,slots.room,speakers,answers.options,submission_type"
ROOMS_URL = f"{URL_BASE}rooms/"
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
SLOT_MINUTES = 10

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
        "780": {
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
    to_remove = ("do_not_record", "notes", "internal_notes",
                 "review_code", "invitation_token", "reviews",
                 "median_score", "mean_score")
    for key in to_remove:
        if key in talk:
            del talk[key]


# Check constants consistency.

assert DAY_START_TIME < DAY_STOP_TIME
assert to_minutes(DAY_START_TIME) % SLOT_MINUTES == 0
assert to_minutes(DAY_STOP_TIME) % SLOT_MINUTES == 0


# Download talks and rooms from API.

talks = []
url = TALKS_URL
for page in range(100):
    print(f"Downloading talks (page #{page})")
    request = Request(url, headers={"Authorization": f"Token {TOKEN}"})
    data = json.loads(urlopen(request).read())
    talks.extend(talk for talk in data["results"] if talk["slots"])
    if not (url := data["next"]):
        break

print("Downloading rooms")
request = Request(ROOMS_URL, headers={"Authorization": f"Token {TOKEN}"})
response = urlopen(request)
rooms = json.loads(response.read())["results"]
rooms_dict = {room["id"]: room for room in rooms}


# Build table for conferences.

print("Generating schedule")
slots = range(to_minutes(DAY_START_TIME), to_minutes(DAY_STOP_TIME), SLOT_MINUTES)
hours = [to_time(minutes) for minutes in slots]
schedule = {day.isoformat(): {to_minutes(hour): {} for hour in hours} for day in CONFERENCE_DAYS}
sprints = {day.isoformat(): {to_minutes(hour): {} for hour in hours} for day in SPRINT_DAYS}
for talk in talks:
    slots = talk["slots"]
    for slot in slots:
        # We assume that talks and schedule share the same timezone.
        if not slot["start"]:
            continue
        start = datetime.fromisoformat(slot["start"])
        end = datetime.fromisoformat(slot["end"])
        clean_talk(talk)
        slot_start_minutes = to_minutes(start) // SLOT_MINUTES * SLOT_MINUTES
        slot_start = to_time(slot_start_minutes)
        if start.date() in CONFERENCE_DAYS:
            schedule[start.date().isoformat()][to_minutes(slot_start)][slot["room"]["id"]] = talk
            rooms_dict[slot["room"]["id"]]["in_conferences"] = True
        elif start.date() in SPRINT_DAYS:
            sprints[start.date().isoformat()][to_minutes(slot_start)][slot["room"]["id"]] = talk
            rooms_dict[slot["room"]["id"]]["in_sprints"] = True
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
