import json
import os

from flask import Flask, render_template

app = Flask(__name__)
AUCTION_ID = os.getenv('AUCTION_ID')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/json')
def serve_json():
    with open(f'games_{AUCTION_ID}.json') as f:
        return json.load(f)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
