# Transcepta: AnyInvoice v2

## Setup

Ensure you have the following dependencies:

- [just](https://just.systems/man/en/), as a `make` alternative to manage script execution.
- [python](https://github.com/asdf-community/asdf-python), consider using asdf to manage the installed Python version
- [pre-commit](https://pre-commit.com/), for linting and other commit checks
- [docker](https://www.docker.com/),
- [poetry](https://python-poetry.org/) to manage the Python environment

Run `just setup` to ensure your environment is correctly set up.

## Testing

Put the following items in the root of the repo:

- `2024-06-20_AI_Testing_3/`
- `2024-07-01_Prod_Infinx_Invoices_2024-6-3to17_AllInfo_v2.json`

Run `just run a_ingestion.py` to ensure everything is setup correctly.
