from __future__ import annotations

import os
import sys
import yaml
import warnings
import polars as pl
from pathlib import Path
from shiny.express import input, render, ui
from shiny import reactive
from algoliasearch.search.client import SearchClient

# needed for posit cloud deployment, which might be
# running shiny app from root of repo.
sys.path.append(str(Path(__file__).parent))

from _utils import query

# TODO: currently we pull the names directly from the repo
# but may want to pull from the index directly.
# (see fetch_all_results() function below)
ALL_PRODUCTS = [entry["name"] for entry in yaml.safe_load(open("./merge_data.yml"))]

INDEX_NAME = os.environ.get("ALGOLIA_INDEX", "shiny-prototype-dev")

client = SearchClient("AK1GB1OWGW", "4ac92cf786d83c1a9bef1d2513c77969")


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


@reactive.calc
async def query_df() -> pl.DataFrame:
    # I don't know what Posit Connect Cloud logs from...
    warnings.warn(f"Querying index: {INDEX_NAME}")
    return await query(client, INDEX_NAME, input.text())

# @reactive.calc
# async def fetch_all_results():
#     all_results = []
#     _ = await client.browse_objects(
#         INDEX_NAME, aggregator=lambda br: all_results.extend(br.hits)
#     )
# 
#     return set([entry["indexName"] for entry in all_results])




@reactive.effect
async def update_product_filter():
    res = await query_df()
    hits = res.unique("breadcrumbs").group_by("indexName").len("n").to_dicts()
    hit_choices = {row["indexName"]: f"{row['indexName']} ({row['n']})" for row in hits}
    all_choices = {k: hit_choices.get(k, f"{k} (0)") for k in ALL_PRODUCTS}

    ui.update_checkbox_group("product_name", choices=all_choices, selected=None)


@reactive.effect
async def update_guide_filter():
    res = await query_df()
    if input.product_name():
        filtered = res.filter(pl.col("indexName").is_in(input.product_name()))
    else:
        filtered = res
    guide_counts = (
        filtered.unique("breadcrumbs")
        .select(guide=pl.col("crumbs").list.get(0))
        .group_by("guide")
        .len("n")
        .to_dicts()
    )

    choices = {row["guide"]: f"{row['guide']} ({row['n']})" for row in guide_counts}

    ui.update_checkbox_group("guide_name", choices=choices, selected=None)


@reactive.calc
async def results():
    res = await query_df()

    final = (
        res.select(
            "title",
            "breadcrumbs",
            "crumbs",
            card=pl.struct(["section", "text", "href"]).map_elements(
                lambda x: html_search_hit_subcard(**x)
            ),
            base=pl.col("indexName"),
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
    )
    return final


async def filtered_results() -> pl.DataFrame:
    res = await results()
    products = input.product_name()
    guides = input.guide_name()

    if products:
        res = res.filter(pl.col("base").is_in(products))
    if guides:
        res = res.filter(
            pl.col("breadcrumbs").str.split(" > ").list.get(1).is_in(guides)
        )

    return res


with ui.layout_sidebar():
    with ui.sidebar(id="left", width=275):
        ui.input_text("text", label="Search", value="SSL workbench")
        ui.input_checkbox_group("product_name", label="Product", choices=[])
        ui.input_checkbox_group("guide_name", label="Product Guide", choices=[])

    @render.text
    def help_why_is_this_happening():
        return INDEX_NAME


    @render.text
    async def row_count():
        res = await filtered_results()
        return f"Results: {len(res)}"

    @render.data_frame
    async def search_results():
        res = await filtered_results()
        return render.DataGrid(
            res.select("card"), filters=True, width="100%", height="80vh"
        )
