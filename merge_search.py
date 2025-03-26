# %%
# This code was supplied by Jeroen
import requests
import json
from pydantic import BaseModel
from urllib import parse
from pathlib import Path

URLS = {
    "base": "https://docs.posit.co/",
    "helm": "https://docs.posit.co/helm/",
    "connect": "https://docs.posit.co/connect/",
    "server-pro": "https://docs.posit.co/ide/server-pro",
}


class SearchItem(BaseModel):
    objectID: str
    href: str  # url to the page (maybe with anchor)
    title: str  # section title
    section: str  # section name
    text: str  # section text
    crumbs: list[str]  # shown in nav display, lists path to nested page


def make_absolute(search_items: list[dict], url: str, index_name: str) -> list[dict]:
    absolute_search_items = []

    for search_item in search_items:
        protocol, domain, *_ = parse.urlsplit(search_item["href"])
        if not protocol and not domain:
            search_item.update(
                {
                    "objectID": f"{url}/{search_item['objectID']}",
                    "indexName": index_name,
                }
            )
        absolute_search_items.append(search_item)

    return absolute_search_items


def shorten_text(text: str, max_length: int) -> str:
    if len(text) > max_length:
        return text[:max_length] + "...SHORTENED"
    return text


merged_search_items = []

for name, url in URLS.items():
    url = url.removesuffix("/")
    r = requests.get(f"{url}/search.json")
    r.raise_for_status()
    search_items = r.json()
    merged_search_items.extend(make_absolute(search_items, url, name))

# %%
with open("docs/search.json", "w") as f:
    json.dump(merged_search_items, f)

with open("docs/search2.json", "w") as f:
    short = [{**d, "text": shorten_text(d["text"], 8_000)} for d in merged_search_items]
    json.dump(short, f)


# %%
