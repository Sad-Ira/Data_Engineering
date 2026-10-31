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
It has its own `notebooks/requirements.txt` (the root dependencies plus `matplotlib`, `seaborn` and `ipykernel`).

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

## Deployment

```bash
# 1. Create a virtual environment in the project folder
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. Install the dependencies
pip install -r requirements.txt              # data_loader.py and scripts/
pip install -r notebooks/requirements.txt    # EDA notebook
```

### Run

```bash
python data_loader.py
```

On the first run `faa_aws.csv` (~175 MB) is downloaded from Google Drive into
the `data/` folder, then the script prints the first 10 rows of the dataset.
Expected output:

```
Dataset size: 316839 rows x 101 columns
```

To open the notebook in VS Code, install the Python and Jupyter extensions, open
`notebooks/EDA.ipynb` and choose the `.venv` kernel in the top right corner.

## Structure

- `data_loader.py` - dataset download, type casting and parquet export
- `notebooks/EDA.ipynb` - exploratory data analysis of the dataset (homework 5) with seaborn charts (homework 6)
- `scripts/read_api.py` - PokeAPI dataset (homework 4), see `scripts/README.md`
- `data/` - local copy of the dataset and the parquet file, created by the script on the first run (not committed to git)
- `requirements.txt` - dependencies of `data_loader.py` and `scripts/`
- `notebooks/requirements.txt` - dependencies of the EDA notebook
- `.gitignore` - keeps the dataset (175 MB), the parquet file and the virtual environment out of git
