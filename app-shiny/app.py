from __future__ import annotations

import polars as pl
import polars.selectors as cs
from shiny.express import input, render, ui
from shiny import reactive
from typing import Callable
from algoliasearch.search.client import SearchClient
from algoliasearch.search.models.hit import Hit

client = SearchClient("GCKGO8JWSW", "6acc5580fcbeba5b8e560c8a546f346d")


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


def hits_to_frame(hits: list[Hit], key_paths: list[str]) -> pl.DataFrame:
    rows = [filter_dict(hit.to_dict(), key_paths) for hit in hits]
    return pl.DataFrame(rows)


def html_search_hit_card(
    title: str, breadcrumbs: str = "bread > crumbs", subcard: str = ""
) -> str:
    return f"""
      <div class="search-result-card">

        <div class="card-body">
            <h3 class="result-title">
            <i class="fa-regular fa-file-lines result-icon"></i>
            {title}
            </h3>
            <div class="result-breadcrumb">{breadcrumbs}</div>

            {subcard}

            </div>
        </div>
      </div>
    """


def html_search_hit_subcard(section: str, text: str, href: str):
    return f"""
        <a href="{href}" class="result-url">
          <div class="result-subcard">
          <h5 class="result-section">{section}</h5>
          <p class="result-text">
          {text}
          </p>
          </div>
        </a>
    """


# App -------------------------------------------------------------------------

ui.tags.style(
    """
a.result-url {
  text-decoration-line: none;
  text-decoration-style: solid;
  text-decoration-color: rgb(51, 51, 51);
  color: rgb(51, 51, 51);
}
a.result-url:hover .result-subcard {
  background-color: papayawhip;
}
"""
)
ui.input_text("text", label="Search", value="SSL workbench")


@reactive.calc
async def results():
    res = await client.search(
        search_method_params={
            "requests": [
                {
                    "indexName": "search",
                    "query": input.text(),
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
        cs.starts_with("_highlight").str.slice(0, 200)
    ).select(
        pl.col("objectID").alias("href"),
        "crumbs",
        "indexName",
        # pl.col("objectID").map_elements(lambda x: ui.tags.a(x, href=x)).alias("url"),
        cs.starts_with("_highlight").name.map(lambda x: x.split(".")[1]),
    )

    final = (
        shortened.select(
            "title",
            "crumbs",
            card=pl.struct(["section", "text", "href"]).map_elements(
                lambda x: html_search_hit_subcard(**x)
            ),
            base=pl.col("indexName"),
        )
        .with_columns(
            breadcrumbs=pl.col("base") + " > " + pl.col("crumbs").list.join(" > ")
        )
        .with_row_index("order")
        .group_by("base", "breadcrumbs", "title")
        .agg(pl.col("order").first(), "card")
        .with_columns(
            card=pl.struct("title", "breadcrumbs", "card").map_elements(
                lambda x: ui.HTML(
                    html_search_hit_card(
                        title=x["title"],
                        breadcrumbs=x["breadcrumbs"],
                        subcard="\n\n".join(x["card"]),
                    )
                )
            ),
        )
        .sort("order")
        .select("card")
    )

    return final


@render.text
async def row_count():
    res = await results()
    return f"Results: {len(res)}"


@render.data_frame
async def search_results():
    res = await results()
    return render.DataGrid(res, filters=True, width="100%", height="80vh")
