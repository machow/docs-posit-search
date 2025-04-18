from __future__ import annotations

import polars as pl
import polars.selectors as cs
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from algoliasearch.search.client import SearchClient
    from algoliasearch.search.models.hit import Hit

# dict helpers ----


def fetch_path(d: dict, key: str, default: Callable):
    """Fetch a nested key from a dictionary, with a default value.

    The use of a default is largely because some search entries lack a "crumb".
    """
    keys = key.split(".")
    try:
        for k in keys:
            d = d[k]
    except KeyError:
        return default()

    return d


def filter_dict(d: dict, keys: dict[str, Callable]) -> dict:
    results = {}
    for key, default in keys.items():
        results[key] = fetch_path(d, key, default)

    return results


# algolia helpers ----


def expr_base_url_path(col: pl.Expr) -> pl.Expr:
    return col.str.split("#").list.get(0)


def hits_to_frame(hits: list[Hit], key_paths: dict[str, Callable]) -> pl.DataFrame:
    rows = [filter_dict(hit.to_dict(), key_paths) for hit in hits]
    return pl.DataFrame(rows)


# query -----


async def query(client: SearchClient, index: str, search: str, limit: int = 200):
    res = await client.search(
        search_method_params={
            "requests": [
                {
                    "indexName": index,
                    "query": search,
                    "hitsPerPage": limit,
                }
            ]
        }
    )

    # Note that these fields are based on the ones in our
    # algolia index. I.e. our search.json has fields named title, section, etc..
    paths = {
        "objectID": str,
        "_highlightResult.title.value": str,
        "_highlightResult.section.value": str,
        "_highlightResult.text.value": str,
        "indexName": str,
        "crumbs": lambda: [""],
    }

    df_search = hits_to_frame(
        res.results[0].actual_instance.hits,
        paths,
    )

    shortened = df_search.with_columns(
        cs.starts_with("_highlight").str.slice(0, 200),
        breadcrumbs=pl.col("indexName") + " > " + pl.col("crumbs").list.join(" > "),
    ).select(
        pl.col("objectID").alias("href"),
        "indexName",
        "breadcrumbs",
        "crumbs",
        # pl.col("objectID").map_elements(lambda x: ui.tags.a(x, href=x)).alias("url"),
        cs.starts_with("_highlight").name.map(lambda x: x.split(".")[1]),
    )

    return shortened
