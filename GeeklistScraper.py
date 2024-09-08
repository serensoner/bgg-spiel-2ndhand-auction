import os
import time
from bs4 import BeautifulSoup
import bbcode
import requests
import xmltodict
from datetime import datetime, timedelta

from Entry import Entry
import logging

from redis_helper import load_from_redis, write_to_redis
from text_utils import send_slack_message, send_discord_message, DISCORD_URL, SLACK_URL

log = logging.getLogger('werkzeug')


class GeeklistScraper:
    geeklist_id: int
    max_timestamp: datetime
    entries: dict[str, Entry] = {}
    key: str = ''
    send_list: list = []

    def __init__(self, auction_id: int, force_scrape: bool = False):
        self.geeklist_id = auction_id
        self.key = f'games_{auction_id}'
        if force_scrape:
            self.parse_all()
        else:
            entries = load_from_redis(self.key)
            self.entries = {str(e['id_']): Entry(**e) for e in entries}

    def parse_all(self):
        self.send_list = []
        parsed = self.parse_geeklist()
        if not parsed.get('geeklist'):
            return False
        log.info('scraping finished')
        items = parsed.get('geeklist').get('item')
        log.info('parsing finished')
        if not items:
            return False

        self.parse_game(items[2605])

        for item in items:
            self.parse_game(item)

        if self.send_list and DISCORD_URL:
            messages = '\n'.join([e.get_message(type_='discord') for e in self.send_list])
            send_discord_message(messages)

        if self.send_list and DISCORD_URL:
            messages = '\n'.join([e.get_message(type_='slack') for e in self.send_list])
            send_slack_message(messages)

        for k in self.entries.keys():
            entry = self.entries[k]
            if entry.last_seen < datetime.now() - timedelta(hours=1):
                entry.deleted = True
                self.entries[k] = entry

        entry_json = list(self.entries.values())
        s = Entry.schema().dumps(entry_json, many=True)
        write_to_redis(self.key, s)

        log.info('Finished scraping')

        return True

    def parse_geeklist(self) -> dict:
        url = f'https://boardgamegeek.com/xmlapi/geeklist/{self.geeklist_id}?comments=1'
        log.info(f'parsing {url}')
        page = requests.get(url)
        if page.status_code == 202:
            log.info(f'Returned 202, sleeping... {self.geeklist_id}')
            return {}
        return xmltodict.parse(page.content)

    def parse_game(self, item_: dict):
        comments = item_.get('comment')
        if comments and type(comments) == dict:
            comments = [comments]

        item_ = {
            'geeklist_id': self.geeklist_id,
            'id_': item_['@id'],
            'subtype': item_['@subtype'],
            'name': item_['@objectname'],
            'username': item_['@username'],
            'post_date': item_['@postdate'],
            'edit_date': item_['@editdate'],
            'body_raw': item_['body'],
            'body_text': BeautifulSoup(
                bbcode.render_html(item_['body']), features='html.parser'
            ).get_text(),
            'body': bbcode.render_html(item_['body']),
            'comments_raw': comments,
        }
        entry = Entry(**item_)
        if str(entry.id_) not in self.entries:
            self.send_list.append(entry)

        self.entries[str(entry.id_)] = entry

    def get_subset(self, **kwargs):
        entries = list(self.entries.values())
        for k, v in kwargs.items():
            entries = [e for e in entries if e.__getattribute__(k) == v]

        return list(reversed(entries))
