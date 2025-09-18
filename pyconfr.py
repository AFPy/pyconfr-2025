import json
from pathlib import Path

from babel.dates import format_date, format_time, format_timedelta
from datetime import date, time, timedelta
from flask import Flask, Response, render_template, url_for
from flask_frozen import Freezer
from flask_weasyprint import render_pdf
from markdown2 import Markdown
from slugify import slugify

YEAR = 2025

app = Flask(__name__, static_url_path=f'/{YEAR}/static')
SCHEDULE = json.loads((Path(app.root_path) / 'schedule.json').read_text())
_GIT_MAIN = Path(app.root_path) / '.git' / 'refs' / 'heads' / 'main'
GIT_VERSION = _GIT_MAIN.read_text().strip()[:7]


@app.template_filter()
def slug(string):
    return slugify(string, max_length=30)


TALK_CATEGORIES = {
    slug(talk['submission_type']['name']['en']): talk['submission_type']
    for dates in
    tuple(SCHEDULE['schedule'].values()) + tuple(SCHEDULE['sprints'].values())
    for hours in dates.values()
    for talk in hours.values()
}


@app.template_filter()
def format_duration(minutes):
    return format_timedelta(
        timedelta(seconds=minutes*60), threshold=10, format='short')


@app.template_filter()
def format_day(day, lang):
    day_date = date.fromisoformat(day)
    return format_date(day_date, format='full', locale=lang)


@app.template_filter()
def format_minutes(minutes, lang):
    hour_time = time(int(minutes) // 60, int(minutes) % 60)
    return format_time(hour_time, format='short', locale=lang)


@app.template_filter()
def markdown(string):
    return Markdown().convert(string)


@app.template_filter()
def ical_datetime(string):
    return string.replace('-', '').replace(':', '').split('+')[0]


@app.template_filter()
def ical_text(string):
    return string.replace('\n', '\n\t')


@app.template_filter()
def version(url):
    return f'{url}?{GIT_VERSION}'


@app.route('/')
@app.route(f'/{YEAR}/')
@app.route(f'/{YEAR}/<lang>/')
@app.route(f'/{YEAR}/<lang>/<name>.html')
def page(name='index', lang='fr'):
    return render_template(
        f'{lang}/{name}.jinja2.html', page_name=name, lang=lang,
        schedule=SCHEDULE)


@app.route(f'/{YEAR}/<lang>/talks/<category>.html')
def talks(lang, category):
    return render_template(
        f'{lang}/talks.jinja2.html', lang=lang, page_name='talks',
        category=category, title=TALK_CATEGORIES[category]['name'][lang],
        schedule=SCHEDULE, categories=TALK_CATEGORIES)


@app.route(f'/{YEAR}/<lang>/full-schedule.html')
def schedule(lang):
    return render_template(
        'schedule.jinja2.html', page_name='full-schedule', lang=lang,
        schedule=SCHEDULE)


@app.route(f'/{YEAR}/<lang>/full-schedule.pdf')
def pdf_schedule(lang):
    return render_pdf(url_for('schedule', lang=lang))


@app.route(f'/{YEAR}/<lang>/calendar.ics')
def calendar(lang):
    ics = render_template('calendar.jinja2.ics', lang=lang, schedule=SCHEDULE)
    return Response(ics, mimetype='text/calendar')


@app.cli.command('freeze')
def freeze():
    Freezer(app).freeze()
