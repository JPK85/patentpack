
# patentpack

Utility for fetching and normalizing patent and assignee data from public APIs.

> [!WARNING]
> This package is highly experimental and probably NOT safe for general installation.

## Quickstart

Count patents for a company in a CPC category:

```bash
# USPTO (PatentsView)
python -m patentpack.cli count-cpc-company-year "BASF SE" --year 2021 --cpc Y02 --provider uspto
# → expect non-negative non-zero integer

# EPO (OPS)
python -m patentpack.cli count-cpc-company-year "TESLA INC" --year 2021 --cpc Y02 --provider epo
# → expect non-negative non-zero integer
```

Or use the Python API directly:

```python
from patentpack.client import PatentPack
from patentpack.core.contracts import Provider

pp = PatentPack(Provider.USPTO, rpm=30)
res = pp.count_cpc_company_year(year=2021, cpc="Y02", company="BASF SE")
print(res.total)
```

## Features

- **USPTO (PatentsView)**: count patents by CPC, year, and assignee
- **EPO (OPS)**: query CPC + applicant across publication years
- **GLEIF**: search LEI records, normalize corporate names, and match assignees
- **Organization Normalization (`orgnorm`)**: canonicalization, stemming, and query expansion for company names

## Project Layout

```
patentpack/
├── scripts/                   # helper scripts
├── src/patentpack/
│   ├── cli.py                 # Typer CLI entrypoint
│   ├── client.py              # PatentPack facade
│   ├── config.py              # environment + defaults
│   ├── core/                  # base contracts & interfaces
│   ├── providers/             # USPTO + EPO provider wrappers
│   ├── gleif/                 # GLEIF search, parse, match
│   └── common/orgnorm/        # normalization & variants
└── tests/                     # pytest + coverage
```

## Setup

Install with Poetry (preferred):

```bash
poetry install
```

or directly in your `conda`/`venv`:

```bash
pip install -e .
```

Environment variables required for usage:

- `PATENTPACK_PV_KEY` ([USPTO PatentsView API key](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/#request-an-api-key))
- `OPS_KEY` / `OPS_SECRET` ([EPO OPS credentials](https://developers.epo.org/))

Set these in an `.env` file at project root or in some other way in your environment.

## Usage

CLI commands:

```bash
# Count BASF Y02 patents in 2021 from USPTO
python -m patentpack.cli count-cpc-company-year "BASF SE" --year 2021 --cpc Y02 --provider uspto

# Count Tesla Y02 patents in 2021 from EPO
python -m patentpack.cli count-cpc-company-year "TESLA INC" --year 2021 --cpc Y02 --provider epo
```

Python API:

```python
from patentpack.client import PatentPack
from patentpack.core.contracts import Provider

pp = PatentPack(Provider.USPTO, rpm=30)
res = pp.count_cpc_company_year(year=2021, cpc="Y02", company="BASF SE")
print(res.total)
```

## Testing

Run tests with `pytest` and `coverage`

```bash
coverage run -m pytest
coverage report -m
```
