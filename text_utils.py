import os

import requests


def remove_tag(text: str, tag: str) -> str:
    start_tag_loc = text.find(f'[{tag}]')
    if start_tag_loc == -1:
        return text

    end_tag_text = f'[/{tag}]'
    end_tag_loc = text.find(end_tag_text)

    removed = f'{text[:start_tag_loc]} {text[end_tag_loc + len(end_tag_text):]}'

    return remove_tag(removed, tag)


def send_slack_message(message):
    url = 'https://hooks.slack.com/services/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'
    requests.post(url, json={'text': message})


def send_discord_message(message: str) -> None:
    url = os.getenv('DISCORD_URL')
    requests.post(url, json={'content': message})
