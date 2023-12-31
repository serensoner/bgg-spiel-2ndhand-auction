from dataclasses import dataclass, field

import bbcode
from dataclasses_json import dataclass_json
from datetime import datetime
from Comment import Comment
import re
from dateutil import parser
from dateutil.parser import ParserError

REGEXES = {
    'language': r'(?:\[b\])?\s*language(?:s)(?:\[\/b\])?\s*:?\s*(?:\[[^\]]*])*([^[\n]*)',
    'condition': r'(?:\[b\])?\s*condition(?:\[\/b\])?\s*:?\s*(?:\[[^\]]*])*([^[\n]*)',
    'starting_bid': r'(?:\[b\])?\s*starting\s*(?:bid)?(?:price)?(?:\[\/b\])?(?:\s*:\s*)?(?:\[[^\]]*])*€?(?:euro)?\s*' +
                    r'(\d+)(?:,-)?€?(?:euro)?(?:[^[\n]*)',
    'soft_res': r'(?:\[b\])?\s*soft\s*(?:reserve)?(?:\[\/b\])?(?:\s*:\s*)?(?:\[[^\]]*])*€\s*(\d+)(?:,-)?(?:[^[\n]*)',
    'hard_res': r'(?:\[b\])?\s*hard\s*(?:reserve)?(?:\[\/b\])?(?:\s*:\s*)?(?:\[[^\]]*])*€\s*(\d+)(?:,-)?(?:[^[\n]*)',
    'bin_price': r'(?:\[b\])?\s*bin\s*(?:price)?(?:\[\/b\])?(?:\s*:\s*)?(?:\[[^\]]*])*€?(?:euro)?\s*(\d+)(?:,-)' +
                 '?(?:[^[\n]*)',
    'auction_end_str': r'(?:\[b\])?\s*auction ends(?:\[\/b\])?\s*:?\s*(?:\[[^\]]*])*([^[\n]*)'
}


def remove_tag(text: str, tag: str) -> str:
    start_tag_loc = text.find(f'[{tag}]')
    if start_tag_loc == -1:
        return text

    end_tag_text = f'[/{tag}]'
    end_tag_loc = text.find(end_tag_text)

    removed = f'{text[:start_tag_loc]} {text[end_tag_loc + len(end_tag_text):]}'

    return remove_tag(removed, tag)


@dataclass_json
@dataclass
class Entry:
    geeklist_id: int = field(repr=False)
    id_: int
    subtype: str = field(repr=False)
    name: str = field(repr=False)
    username: str = field(repr=False)
    post_date: datetime | str = field(repr=False)
    edit_date: datetime | str = field(repr=False)
    body_raw: str = field(repr=False)
    body_text: str
    post_date_json: str = None
    edit_date_json: str = None
    auction_end_json: str = None
    body: str = field(default=None, repr=False)
    comments_raw: list[dict] = field(default=None, repr=False)
    language: str = ''
    condition: str = ''
    starting_bid: float = None
    soft_res: float = None
    hard_res: float = None
    bin_price: float = None
    auction_end_str: str = field(default=None, repr=False)
    auction_end: datetime = field(default=None, repr=False)
    comments: list[Comment] = field(default=None, repr=False)
    comments_json: list[str] = field(default=None, repr=False)
    bids: list[Comment] = field(default=None, repr=False)
    max_bid: float = None
    current: float = None
    max_bidder: str = None
    is_sold: bool = False
    last_seen: datetime = field(default=datetime.now(), repr=False)
    deleted: bool = False
    is_ended: bool = False

    def remove_strikethroughs(self):
        self.body = remove_tag(self.body_raw, '-')

    def assign_field(self, field_name):
        groups = re.search(REGEXES[field_name], self.body, re.IGNORECASE)
        if groups:
            setattr(self, field_name, groups.group(1).strip())

    def __post_init__(self):
        self.remove_strikethroughs()
        if not self.body or len(self.body) < 100:
            self.is_ended = True

        for k in REGEXES.keys():
            self.assign_field(k)

        for k in ['starting_bid', 'soft_res', 'hard_res', 'bin_price']:
            try:
                setattr(self, k, float(getattr(self, k)))
            except:
                pass

        self.post_date = parser.parse(self.post_date)
        self.post_date_json = self.post_date.strftime('%b %d')
        self.edit_date = parser.parse(self.edit_date)
        self.edit_date_json = self.edit_date.strftime('%b %d')
        if self.auction_end_str:
            try:
                self.auction_end = parser.parse(self.auction_end_str, fuzzy=True)
                self.auction_end_json = self.auction_end.strftime('%b %d')
            except ParserError:
                self.auction_end = datetime(2099, 12, 31)

            self.is_ended = self.auction_end < datetime.now().today()

        if self.comments_raw:
            self.comments = [Comment(
                username=c['@username'], date_str=c['@date'], postdate_str=c['@postdate'],
                editdate_str=c['@editdate'], text=c.get('#text', ''),
                text_render=bbcode.render_html(c.get('#text', '')),
                entry_username=self.username, entry_bin=self.bin_price
            ) for c in self.comments_raw]
            self.comments_json = [
                f'{c.post_date_json} - {c.username}: {c.text_render}'
                for c in self.comments
            ]
            self.bids = [c for c in self.comments if c.bid]
            if self.bids:
                self.max_bid = max([m.bid for m in self.bids])
                self.max_bidder = next(m.username for m in self.bids if m.bid == self.max_bid)
                if self.bin_price:
                    self.is_sold = self.max_bid >= self.bin_price
                    self.is_ended = self.is_sold

        self.current = self.max_bid if self.max_bid else self.starting_bid
