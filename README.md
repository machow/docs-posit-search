# Posit documentation federated search

This repo experiments with combining search across multiple posit.co documentation sites.
It's not meant to be used for important situations, but to prototype ways of improving search with Quarto.

## Starter applications

There are two folders with starter applications:

- `app-shiny`: A basic Python Shiny app, that queries algolia and dumps the raw results.
- `app-vue`: A basic Vue application.

## Where does the algolia index live?

Currently, it lives on Michael's free algolia account. Once he gets access to a Posit algolia project, he can move it there. Because it's on a free account, he had to truncate some longer text fields.
