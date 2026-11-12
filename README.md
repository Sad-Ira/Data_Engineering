# Data_Engineering

Repository for the ITMO Engineering Data Management project.

[PROJECT DATASET (Google Drive)](https://drive.google.com/file/d/1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn/view?usp=sharing)

- **File:** `faa_aws.csv`, downloadable size ≈ **175 MB**
- **Content:** over 300,000 records of wildlife (bird/animal) strikes with civil aircraft in the USA - incident date and location, aircraft details, flight phase, environmental conditions, wildlife species involved

## Homework 2 - data loader

The script `data_loader.py` downloads the dataset from Google Drive with `gdown` (the file is too large for a direct download link) and reads it with `pandas`. On the first run `faa_aws.csv` is saved to the `data/` folder, the following runs reuse the local copy. The script prints the first 10 rows of the table and its size.

Requires Python 3.9+.

## Homework 3 - data types and parquet

The script was extended with:

- `read_dataset` - short wrapper around `pd.read_csv`;
- `convert_types` - casts columns to proper dtypes and returns a new DataFrame:
  `INCIDENT_DATE` becomes `datetime`, integer-like columns become nullable `Int64`,
  money/coordinates/distance become `float64`, columns with few unique values
  become `category`;
- `save_parquet` - writes the resulting DataFrame to `data/faa_aws.parquet`.

The parquet file is 38 MB vs 167 MB for the CSV, and it keeps the dtypes on
`pd.read_parquet` without re-parsing. It lives in `data/`, which is ignored
by git, so the binary file never gets into the repository.

## Homework 5 - EDA

`notebooks/EDA.ipynb` - exploratory analysis of `faa_aws.csv` from the data quality side:
structure and types, missing values and duplicates, outliers, consistency between fields,
quality metrics and what to fix in the ETL pipeline.

The notebook reads `data/faa_aws.csv` and downloads it with `data_loader.py` if the file is missing.
Its libraries (`matplotlib`, `seaborn`, `ipykernel`) are in the `dev` block of `pyproject.toml`.

## Homework 6 - visualization

The charts in `notebooks/EDA.ipynb` are drawn with `seaborn` (matplotlib only sets figure size and titles).
Besides the redrawn ones, new charts show the data problems found in the EDA:

- reports per year and month (heatmap) - seasonality and the incomplete end of the export;
- missing values by year (heatmap) - completeness changes over time, the jump of empty `COMMENTS` in 2019;
- `HEIGHT` by flight phase (boxplot) - why a global IQR fence does not fit this data;
- repair cost on a log scale and `SPEED` distribution - log-normal costs and rounded speeds;
- airport coordinates (scatter) - the airport with a flipped longitude sign;
- `TIME_OF_DAY` by hour of `TIME` - contradictions that look like the 12-hour time format;
- damaged-but-not-struck flags by aircraft part;
- correlation heatmap, quality metrics vs targets and the time to the last update (ECDF).

## Homework 7 - PostgreSQL

The upload is split into two scripts:

- `scripts/read_creds.py` reads the `homeworks` account from the SQLite table
  `access` in `creds.db` and saves it to the local `.env` file as
  `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` and `DB_NAME`;
- `scripts/write_to_db.py` takes these variables from `.env`, reads the first
  100 rows of `data/faa_aws.parquet` and writes them to the PostgreSQL table
  `aibatovais`. It does not overwrite an existing table.

The parquet file keeps the dtypes set in `data_loader.py`, so the table gets
proper column types (timestamp, integer, boolean) instead of plain text.

Install the dependencies as described below and create the parquet file
if it is not there yet (`python data_loader.py`). Then, from the repository root:

```bash
python scripts/read_creds.py /absolute/path/to/creds.db
python scripts/write_to_db.py
```

`read_creds.py` only needs to be run once, other variables in `.env` are kept.
Keep `creds.db` outside the repository. Both `.env` and `creds.db` are ignored
by git. Never commit access credentials.

## Homework 8 - ETL package

The `etl` package in `src/` runs the whole data preparation cycle in one command:
it downloads the raw dataset, cleans it, validates the result, saves the clean
parquet file and writes a sample (100 rows max) to PostgreSQL. The package does
not import the old scripts, the useful code from `data_loader.py` (homeworks 2-3)
and `scripts/` (homework 7) is moved inside it.

### Package structure

```text
src/etl/
├── __init__.py    package description and version
├── extract.py     download faa_aws.csv from Google Drive (once) and read it
├── transform.py   cleaning and type casting, the steps come from the EDA
├── validate.py    checks of the clean data, all problems are reported together
├── load.py        save the clean parquet, build the DB URL from .env, write the sample
├── creds.py       copy the PostgreSQL access from creds.db to .env
└── main.py        command line entry point, runs extract -> transform -> validate -> load
```

### What happens to the data

`transform.py` follows the recommendations from section 8 of the EDA:

1. strings are trimmed (`AC_CLASS` was `'A  '`), blank strings become `NaN`
   (`TIME` had 14 105 values of only spaces);
2. placeholders become `NaN`: `ZZZZ` / `UNKNOWN` airport, `UNK` / `UNKNOWN` operator,
   `UNKNOWN` aircraft, `Unknown` in `WARNED`;
3. constant columns `REPORTED_NAME`, `REPORTED_TITLE`, `TRANSFER` are dropped;
4. 61 reports sent twice with a new `INDEX_NR` are dropped;
5. coordinates in other formats (7 rows) become `NaN`, the airport in Kansas
   with a flipped longitude sign is fixed;
6. `None` is removed from precipitation lists like `None, Rain`;
7. types are cast: dates, nullable integers, floats, booleans, categories;
   `NUM_SEEN` and `NUM_STRUCK` are ranges (`2-10`), so they become ordered categories;
8. a part that is damaged or ingested something is marked as struck;
9. contradictions that can't be fixed for sure are flagged, not changed:
   `FLAG_TIME_CONFLICT` (night at noon, day at 2 am) and
   `FLAG_UPDATED_BEFORE_INCIDENT`.

`validate.py` then checks the required columns, dtypes, unique `INDEX_NR`,
no duplicates, value ranges (coordinates, month, year, height, speed, costs),
month and year against the date, damaged parts against struck ones and extra
spaces in strings. If something fails, the pipeline stops before the database.

Result: 316 778 rows x 100 columns in `data/faa_aws_clean.parquet` (38 MB),
the first rows go to the table `aibatovais`.

### Run

Install the package as described in [Deployment](#deployment), then from the
repository root:

```bash
# first run: copy the database access from creds.db to .env and load 100 rows
etl --creds /absolute/path/to/creds.db

# next runs take the access from .env
etl --rows 50 --if-exists replace

# only download, clean and validate, without the database
etl --skip-db
```

`python -m etl.main ...` works the same way. Arguments:

| argument | default | description |
|---|---|---|
| `--rows` | `100` | how many rows to write to the database, 1-100 |
| `--table` | `aibatovais` | PostgreSQL table name |
| `--if-exists` | `fail` | `fail` keeps an existing table, `replace` overwrites it, `append` adds rows |
| `--data-dir` | `data` | folder for the raw CSV and the clean parquet |
| `--creds` | - | path to `creds.db`, copies the access to `.env` before loading |
| `--skip-db` | off | stop after the parquet file |

The table `aibatovais` already exists after homework 7, so use
`--if-exists replace` to write the clean data there. The database access is
checked before the data is processed, so a missing `.env` is reported at once.

Tests: `pytest` (they don't need the dataset or the database).

## Deployment

```bash
# 1. Create a virtual environment in the project folder
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. Install the etl package with its dependencies
pip install -e .

# or together with the dev block: tests, linter, EDA notebook, homework 4 script
pip install -e ".[dev]"
```

All dependencies are in `pyproject.toml`: `dependencies` is what the ETL needs
to run, the `dev` block has the service libraries (`pytest`, `ruff`, `ipykernel`,
`matplotlib`, `seaborn`, `requests`).

### Run

```bash
etl --skip-db
```

On the first run `faa_aws.csv` (~175 MB) is downloaded from Google Drive into
the `data/` folder, the next runs reuse it. See [Homework 8](#homework-8---etl-package)
for loading to the database.

The old loader from homeworks 2-3 still works: `python data_loader.py`.

To open the notebook in VS Code, install the Python and Jupyter extensions, open
`notebooks/EDA.ipynb` and choose the `.venv` kernel in the top right corner.

## Structure

```text
Data_Engineering/
├── src/etl/              ETL package (homework 8), see "Package structure" above
├── tests/                pytest tests of the etl package
├── notebooks/EDA.ipynb   exploratory data analysis (homework 5) with seaborn charts (homework 6)
├── scripts/              read_api.py (homework 4), read_creds.py and write_to_db.py (homework 7)
├── data_loader.py        dataset download, type casting and parquet export (homeworks 2-3)
├── data/                 raw CSV and parquet files, created on the first run (not in git)
├── pyproject.toml        package settings, dependencies and the dev block
├── .env                  database access, created by etl --creds (not in git)
└── .gitignore            keeps data, .env, creds.db and the virtual environment out of git
```
