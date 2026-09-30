# Data_Engineering

Repository for the ITMO Engineering Data Management project.

[PROJECT DATASET (Google Drive)](https://drive.google.com/file/d/1jlokcbHZhYYWDbnIRqdPGTLnmCJ8Upjn/view?usp=sharing)

- **File:** `faa_aws.csv`, downloadable size ≈ **175 MB**
- **Content:** over 300,000 records of wildlife (bird/animal) strikes with civil aircraft in the USA - incident date and location, aircraft details, flight phase, environmental conditions, wildlife species involved

## Homework 2 - data loader

The script `data_loader.py` downloads the dataset from Google Drive with `gdown` (the file is too large for a direct download link) and reads it with `pandas`. On the first run `faa_aws.csv` is saved to the project folder, the following runs reuse the local copy. The script prints the first 10 rows of the table and its size.

Requires Python 3.9+.

### Deployment

```bash
# 1. Create a virtual environment in the project folder
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 3. Install the dependencies
pip install -r requirements.txt
```

### Run

```bash
python data_loader.py
```

On the first run `faa_aws.csv` (~175 MB) is downloaded from Google Drive into
the current folder, then the script prints the first 10 rows of the dataset.
Expected output:

```
Dataset size: 316839 rows x 101 columns
```

## Structure

- `data_loader.py` - dataset download and preview
- `requirements.txt` - dependencies
- `.gitignore` - keeps the dataset (175 MB) and the virtual environment out of git
