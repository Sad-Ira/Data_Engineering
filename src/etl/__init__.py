"""ETL pipeline for the FAA Wildlife Strike dataset.

extract -> transform -> validate -> load:

- ``extract``   downloads the raw CSV from Google Drive and reads it;
- ``transform`` cleans the data and casts the columns to proper dtypes;
- ``validate``  checks the result before it leaves the pipeline;
- ``load``      saves the clean parquet file and writes a sample to PostgreSQL;
- ``creds``     copies PostgreSQL access from ``creds.db`` to ``.env``;
- ``main``      command line entry point that runs all the steps.
"""

__version__ = "0.1.0"
