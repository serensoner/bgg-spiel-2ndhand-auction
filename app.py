import os
from flask_apscheduler import APScheduler
import datetime as dt
from flask import Flask, render_template, request, jsonify

from Geeklister import refresh_geeklist
from redis_helper import load_from_redis, write_to_redis
from logger import logger

app = Flask(__name__)
GEEKLIST_ID = os.getenv('AUCTION_ID')
# TODO PARSE IS SOLD AS WELL 11056867

@app.route('/')
def home():
    return render_template('index.html', geeklist_id=GEEKLIST_ID)


@app.post('/shortlist/<username>')
def shortlist_action(username: str):
    action = request.form.get('action')
    game_id = request.form.get('game_id')
    shortlist = load_from_redis(f'SPIEL2025_SHORTLIST_{username}')
    if action == 'add':
        logger.info(f"{username} added {game_id}")
        shortlist = f'{shortlist};{game_id}'
    if action == 'remove':
        shortlist = shortlist.split(';')
        shortlist.remove(str(game_id))
        logger.info(f"{username} removed {game_id}")
        shortlist = ';'.join(shortlist)
    write_to_redis(f'SPIEL2025_SHORTLIST_{username}', shortlist)
    return '', 200


@app.get('/load_shortlist/<username>')
def load_shortlist(username: str):
    logger.info(f"{username} loaded shortlist")
    shortlist = load_from_redis(f'SPIEL2025_SHORTLIST_{username}')
    return jsonify({"shortlist": shortlist})


@app.route('/json/<username>')
def serve_json(username: str):
    logger.info(f"{username} loaded json")
    games = load_from_redis(f'games_{GEEKLIST_ID}')

    shortlist = load_from_redis(f'SPIEL2025_SHORTLIST_{username}')
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


@scheduler.task('interval', id='scrape', seconds=10, misfire_grace_time=60, max_instances=1)
def job1():
    refresh_geeklist(GEEKLIST_ID, force_scrape=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
