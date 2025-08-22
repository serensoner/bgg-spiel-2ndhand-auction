from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
import xmltodict
from bs4 import BeautifulSoup

from Entry import Entry
from redis_helper import load_from_redis, write_to_redis
from text_utils import send_slack_message, send_discord_message, DISCORD_URL, SLACK_URL
import bbcode
import logging

from logger import logger

AUCTION_ID = os.getenv("AUCTION_ID")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
DISCORD_URL: Optional[str] = None  # set externally
SLACK_URL: Optional[str] = None    # set externally


class GeeklistScraper:
    geeklist_id: str
    attempt: int

    def __init__(self, geeklist_id: str):
        self.geeklist_id = geeklist_id
        self.attempt = 0

    def scrape(self) -> dict:
        url = f"https://boardgamegeek.com/xmlapi/geeklist/{self.geeklist_id}?comments=1&attempt={self.attempt}"
        logger.info(f"scraping {url}")
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
            timeout=30
        )
        if resp.status_code == 202:
            self.attempt += 1
            logger.info(f"Returned 202 (BGG building feed). {self.attempt=} geeklist_id={self.geeklist_id}")
            return {}
        resp.raise_for_status()
        self.attempt = 0
        return xmltodict.parse(resp.content)


@dataclass
class GeeklistParser:
    geeklist_id: str
    force_scrape: bool = False
    key: str = field(init=False)
    key_full: str = field(init=False)

    # runtime state (instance-only; no mutable class vars!)
    entries: Dict[str, "Entry"] = field(default_factory=dict)    # id_ -> Entry
    send_list: List["Entry"] = field(default_factory=list)

    # serialization behavior
    skipped_keys: List[str] = field(default_factory=lambda: [
        "body_cleaned", "body_raw", "auction_end", "auction_end_str",
        "body_text", "comments", "comments_raw", "bids", "condition"
    ])

    def __post_init__(self):
        self.key = f"games_{self.geeklist_id}"
        self.key_full = f"games_{self.geeklist_id}_full"

        if not self.force_scrape:
            cached = load_from_redis(self.key) or []
            # Rehydrate entries as already-parsed
            self.entries = {
                str(e["id_"]): Entry(**{**e, **{"is_parsed": True}})
                for e in cached
            }

    def parse_all(self, scraped: dict) -> bool:
        self.send_list.clear()

        geeklist = scraped.get("geeklist") if scraped else None
        if not geeklist:
            logger.error("No geeklist in payload")
            return False

        items = geeklist.get("item")
        if not items:
            logger.error("No items in geeklist")
            return False

        if isinstance(items, dict):
            items = [items]

        for item in items:
            logger.debug(f"""Parsing {item.get("@id")}""")
            self._parse_game(item)

        self._notify()
        self._mark_deleted()
        self._persist()

        logger.info("Finished parsing & persistence")
        return True

    def get_subset(self, **filters) -> List["Entry"]:
        filtered = list(self.entries.values())
        for k, v in filters.items():
            filtered = [e for e in filtered if getattr(e, k) == v]
        return list(reversed(filtered))

    def _parse_game(self, item: dict) -> None:
        comments = item.get("comment")
        if comments and isinstance(comments, dict):
            comments = [comments]

        data = {
            "geeklist_id": self.geeklist_id,
            "id_": item["@id"],
            "subtype": item.get("@subtype"),
            "name": item.get("@objectname"),
            "username": item.get("@username"),
            "post_date": item.get("@postdate"),
            "edit_date": item.get("@editdate"),
            "body_raw": item.get("body"),
            "body_text": BeautifulSoup(
                item.get("body"), features="html.parser"
            ).get_text(),
            "body": bbcode.render_html(item.get("body") or ""),
            "comments_raw": comments,
            "is_sold": bool(int(item.get("@sold", "0")))
        }

        entry = Entry(**data)
        key = str(entry.id_)

        if key not in self.entries:
            self.send_list.append(entry)

        self.entries[key] = entry

    def _notify(self) -> None:
        if self.send_list:
            if DISCORD_URL:
                messages = "\n".join(e.get_message(type_="discord") for e in self.send_list)
                send_discord_message(messages)
            if SLACK_URL:
                messages = "\n".join(e.get_message(type_="slack") for e in self.send_list)
                send_slack_message(messages)

    def _mark_deleted(self) -> None:
        cutoff = datetime.now() - timedelta(hours=1)
        for k, entry in list(self.entries.items()):
            if getattr(entry, "last_seen", datetime.min) < cutoff:
                entry.deleted = True
                self.entries[k] = entry

    def _persist(self) -> None:
        entry_list = list(self.entries.values())
        write_to_redis(
            self.key_full,
            [{k: v for k, v in e.__dict__.items()} for e in entry_list],
        )
        write_to_redis(
            self.key,
            [
                {k: v for k, v in e.__dict__.items() if k not in self.skipped_keys}
                for e in entry_list
            ],
        )


def refresh_geeklist(geeklist_id: str, force_scrape: bool = False) -> bool:
    scraper = GeeklistScraper(geeklist_id)
    scraped = scraper.scrape()
    if not scraped:
        logger.info("scraped empty, not parsing")
        return False

    parser = GeeklistParser(geeklist_id, force_scrape=force_scrape)
    logger.info("parser created")
    parser.parse_all(scraped)
    logger.info("parsed")
