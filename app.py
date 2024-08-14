import json
import os
from flask_apscheduler import APScheduler
import datetime as dt
from flask import Flask, render_template, request, jsonify

from GeeklistScraper import GeeklistScraper
from redis_helper import load_from_redis, write_to_redis

app = Flask(__name__)
GEEKLIST_ID = os.getenv('AUCTION_ID')
geeklist = GeeklistScraper(int(GEEKLIST_ID))


@app.route('/')
def home():
    return render_template('index.html', geeklist_id=GEEKLIST_ID)


@app.post('/shortlist/<username>')
def shortlist_action(username: str):
    action = request.form.get('action')
    game_id = request.form.get('game_id')
    shortlist = load_from_redis(f'SPIEL2024_SHORTLIST_{username}')
    if action == 'add':
        shortlist = f'{shortlist};{game_id}'
    if action == 'remove':
        shortlist = shortlist.split(';')
        shortlist.remove(str(game_id))
        shortlist = ';'.join(shortlist)
    write_to_redis(f'SPIEL2024_SHORTLIST_{username}', json.dumps(shortlist))
    return '', 200


@app.post('/add_to_shortlist/<username>')
def add_to_shortlist(username: str):
    game_id = request.form.get('game_id')
    shortlist = load_from_redis(f'SPIEL2024_SHORTLIST_{username}')
    shortlist = f'{shortlist};{game_id}'
    write_to_redis(f'SPIEL2024_SHORTLIST_{username}', json.dumps(shortlist))
    return render_template('index.html', geeklist_id=GEEKLIST_ID)


@app.get('/load_shortlist/<username>')
def load_shortlist(username: str):
    shortlist = load_from_redis(f'SPIEL2024_SHORTLIST_{username}')
    return jsonify({"shortlist": shortlist})


@app.route('/json/<username>')
def serve_json(username: str):
    games = load_from_redis(f'games_{GEEKLIST_ID}')

    shortlist = load_from_redis(f'SPIEL2024_SHORTLIST_{username}')
    shortlist = shortlist.split(';') if shortlist else []

    today_tomorrow = request.args.get('todaytomorrow', False)
    if today_tomorrow:
        today_tomorrow = [
            dt.datetime.today().strftime('%b %d'),
            (dt.datetime.today() + dt.timedelta(days=1)).strftime('%b %d')
        ]
        return [g for g in games if g['auction_end_json'] in today_tomorrow]

    return [{**g, **{'shortlist': str(g['id_']) in shortlist}} for g in games]


scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@scheduler.task('interval', id='scrape', seconds=5, misfire_grace_time=60, max_instances=1)
def job1():
    geeklist.parse_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
