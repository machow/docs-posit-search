from shiny.express import input, render, ui
from algoliasearch.search.client import SearchClient
from pprint import pformat

client = SearchClient("GCKGO8JWSW", "6acc5580fcbeba5b8e560c8a546f346d")

ui.input_slider("val", "Slider label", min=0, max=100, value=50)


@render.text
def slider_val():
    return f"Slider value: {input.val()}"


@render.code
async def search_results():
    res = await client.search(
        search_method_params={
            "requests": [
                {
                    "indexName": "search",
                    "query": "test",
                }
            ]
        }
    )

    return pformat(
        res.to_dict(),
    )
