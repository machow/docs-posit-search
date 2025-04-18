import json
import os
from dotenv import load_dotenv
from algoliasearch.search.client import SearchClientSync

load_dotenv()

INDEX_NAME = os.environ.get("ALGOLIA_INDEX", "shiny-prototype-dev")

# %% load search.json ----
objects = json.load(open("docs/search2.json"))
batch_ops = [
    {"action": "addObject", "body": obj} for obj in objects
]


# %% replace index ----
# Initialize the client
# In an asynchronous context, you can use SearchClient instead, which exposes the exact same methods.
client = SearchClientSync(
    os.environ["ALGOLIA_APP_ID"],
    os.environ["ALGOLIA_API_KEY_WRITE"],
)

# Call the API
response = client.clear_objects(
    index_name=INDEX_NAME,
)


client.batch(
    index_name=INDEX_NAME,
    batch_write_params={
        "requests": batch_ops
    }
)
# %%
