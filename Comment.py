import re
from dataclasses import dataclass, field
from datetime import datetime

from dataclasses_json import dataclass_json
from dateutil import parser


@dataclass_json
@dataclass
class Comment:
    username: str
    date_str: str = field(repr=False)
    postdate_str: str = field(repr=False)
    editdate_str: str = field(repr=False)
    text: str = field(repr=False)
    entry_username: str = field(repr=False)
    text_render: str = field(default='')
    date: datetime = None
    post_date: datetime = field(default=None, repr=False)
    post_date_json: str = None
    edit_date: datetime = field(default=None, repr=False)
    edit_date_json: str = None
    entry_bin: float = field(default=None, repr=False)
    is_bin: bool = field(default=None, repr=False)
    bid: float = None

    def extract_bid(self):
        text = self.text
        s = re.search(r'\[.*=\d+\]', self.text, re.IGNORECASE)
        if s:
            text = text.replace(s.group(), '')
        regexes = [
            r'(?:€\s*(\d+))|(?:(\d+)\s*€)',
            r'(?:\b(?:euros?)\s*(\d+))|(?:(\d+)\s*(?:euros?))\b',
            r'(?:\b[E]\s*(\d+))|(?:(\d+)\s*[E]\b)',
            r'(?:\b(\d+)\b)'
        ]
        for r in regexes:
            ext = re.search(r, text, re.IGNORECASE)
            if ext:
                v = ext.group().strip()
                f = re.findall(r'\d+', v)
                if f:
                    return float(f[0])

    def __post_init__(self):
        if self.username == self.entry_username:
            return

        if re.search(r'\b(bin)\b', self.text, re.IGNORECASE):
            self.is_bin = True

        self.bid = self.extract_bid()

        if self.is_bin and self.entry_bin:
            self.bid = self.entry_bin

        self.date = parser.parse(self.date_str)
        self.post_date = parser.parse(self.postdate_str)
        self.post_date_json = self.post_date.strftime('%b %d')
        self.edit_date = parser.parse(self.editdate_str)
        self.edit_date_json = self.edit_date.strftime('%b %d')

