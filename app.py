import json
import os
from flask_apscheduler import APScheduler
import datetime as dt
from flask import Flask, render_template, request

from GeeklistScraper import GeeklistScraper

app = Flask(__name__)
AUCTION_ID = os.getenv('AUCTION_ID')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/json')
def serve_json(ids: str = None, todaytomorrow: bool = False):
    with open(f'games_{AUCTION_ID}.json') as f:
        games = json.load(f)

    today_tomorrow = request.args.get('todaytomorrow', False)
    if today_tomorrow:
        today_tomorrow = [
            dt.datetime.today().strftime('%b %d'),
            (dt.datetime.today() + dt.timedelta(days=1)).strftime('%b %d')
        ]
        return [g for g in games if g['auction_end_json'] in today_tomorrow]

    ids = request.args.get('ids', None)
    if not ids:
        return games

    ids = ids.split(';')
    return [g for g in games if str(g['id_']) in ids]


scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@scheduler.task('interval', id='scrape', seconds=300, misfire_grace_time=900)
def job1():
    GeeklistScraper(int(os.getenv('AUCTION_ID')), force_scrape=True)


if __name__ == '__main__':
    GeeklistScraper(int(os.getenv('AUCTION_ID')), force_scrape=True)
    app.run(host='0.0.0.0', port=8080)
