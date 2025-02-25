# %%
# This code was supplied by Jeroen
import requests
import json
from pydantic import BaseModel
from urllib import parse
from pathlib import Path


class SearchItem(BaseModel):
    objectID: str
    href: str  # url to the page (maybe with anchor)
    title: str  # section title
    section: str  # section name
    text: str  # section text
    crumbs: list[str]  # shown in nav display, lists path to nested page


urls = [
    "https://docs.posit.co/",
    "https://docs.posit.co/helm/",
    "https://docs.posit.co/connect/",
    "https://docs.posit.co/ide/server-pro",
]


def make_absolute(search_items: list[dict], url: str) -> list[dict]:
    absolute_search_items = []

    for search_item in search_items:
        protocol, domain, *_ = parse.urlsplit(search_item["href"])
        if not protocol and not domain:
            search_item.update(
                {
                    "objectID": f"{url}/{search_item['objectID']}",
                    "href": f"{url}/{search_item['href']}",
                }
            )
        absolute_search_items.append(search_item)

    return absolute_search_items


merged_search_items = []

for url in urls:
    url = url.removesuffix("/")
    r = requests.get(f"{url}/search.json")
    r.raise_for_status()
    search_items = r.json()
    merged_search_items.extend(make_absolute(search_items, url))

# %%
with open("docs/search.json", "w") as f:
    json.dump(merged_search_items, f)

# %%
