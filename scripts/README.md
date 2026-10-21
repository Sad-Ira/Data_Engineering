# Homework 4 - collecting a dataset from a public API

The script `read_api.py` collects a dataset of the first-generation pokemon
(Kanto, #1-151) from [PokéAPI](https://pokeapi.co), a free API that needs no key
or registration (found in the [public-apis](https://github.com/public-apis/public-apis) list).

How it works:

1. `GET /api/v2/pokemon?limit=151` returns the list of pokemon with links to their cards;
2. each card `GET /api/v2/pokemon/{id}` is requested one by one with a 0.2 s pause,
   a failed card is printed and skipped instead of stopping the whole run;
3. every card is flattened into one row: name, types, height, weight, base experience
   and six base stats;
4. `convert_types` casts the columns to proper dtypes, 12 sprites are downloaded
   for the preview, the table is saved to `data/pokemon.csv`.

Height and weight come from the API in decimetres and hectograms, the script
converts them to metres and kilograms.

## Dataset

| column | dtype | description |
|---|---|---|
| `id` | `Int64` | pokedex number |
| `name` | `object` | pokemon name |
| `type_1`, `type_2` | `category` | main and secondary type, `type_2` is empty for single-type pokemon |
| `height_m`, `weight_kg` | `float64` | height in metres and weight in kilograms |
| `base_experience` | `Int64` | experience for defeating the pokemon |
| `hp`, `attack`, `defense`, `special_attack`, `special_defense`, `speed` | `Int64` | base stats |
| `total_stats` | `Int64` | sum of the six base stats |
| `sprite_url` | `object` | link to the sprite image |

Result: 151 rows x 15 columns, `data/pokemon.csv` (~20 KB), sprites in
`data/pokemon_sprites/`. The `data/` folder is ignored by git.

## Run

From the repository root, with the virtual environment activated
(see [Deployment](../README.md#deployment) in the main README):

```bash
pip install -r requirements.txt
python scripts/read_api.py
```

All dependencies, including `requests` used by this script, are listed in the
root `requirements.txt`. The full run takes about 2 minutes.

## Output

First 10 rows of the dataset:

![dataset head](https://github.com/user-attachments/assets/d98191b6-1e60-482e-b0ea-38a9326cc4f7)

Downloaded sprites:

![sprites](https://github.com/user-attachments/assets/2428794a-5372-479f-b13e-3e186860e3ea)
