import json
import os
from flask_apscheduler import APScheduler

from flask import Flask, render_template

from GeeklistScraper import GeeklistScraper

app = Flask(__name__)
AUCTION_ID = os.getenv('AUCTION_ID')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/json')
def serve_json():
    with open(f'games_{AUCTION_ID}.json') as f:
        return json.load(f)


scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@scheduler.task('interval', id='scrape', seconds=300, misfire_grace_time=900)
def job1():
    GeeklistScraper(os.getenv('AUCTION_ID')).parse_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
