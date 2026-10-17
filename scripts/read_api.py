import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://pokeapi.co/api/v2"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "pokemon.csv"
SPRITES_DIR = DATA_DIR / "pokemon_sprites"

POKEMON_LIMIT = 151
SPRITES_LIMIT = 12
REQUEST_DELAY = 0.2
TIMEOUT = 15

STAT_NAMES = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]


def fetch_pokemon_urls(limit: int = POKEMON_LIMIT) -> list[str]:
    response = requests.get(
        f"{BASE_URL}/pokemon",
        params={"limit": limit},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return [item["url"] for item in response.json()["results"]]


def extract_row(pokemon: dict) -> dict:
    stats = {stat["stat"]["name"]: stat["base_stat"] for stat in pokemon["stats"]}
    types = sorted(pokemon["types"], key=lambda item: item["slot"])
    sprite = pokemon["sprites"].get("front_default")

    return {
        "id": pokemon["id"],
        "name": pokemon["name"],
        "type_1": types[0]["type"]["name"],
        "type_2": types[1]["type"]["name"] if len(types) > 1 else pd.NA,
        # the API returns height in decimetres and weight in hectograms
        "height_m": pokemon["height"] / 10,
        "weight_kg": pokemon["weight"] / 10,
        "base_experience": pokemon["base_experience"],
        "hp": stats["hp"],
        "attack": stats["attack"],
        "defense": stats["defense"],
        "special_attack": stats["special-attack"],
        "special_defense": stats["special-defense"],
        "speed": stats["speed"],
        "total_stats": sum(stats[name] for name in STAT_NAMES),
        "sprite_url": sprite,
    }


def fetch_dataset() -> pd.DataFrame:
    urls = fetch_pokemon_urls()
    rows = []

    for i, url in enumerate(urls, start=1):
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            rows.append(extract_row(response.json()))
        except (requests.RequestException, KeyError, ValueError) as error:
            print(f"Failed to fetch {url}: {error}")

        if i % 25 == 0:
            print(f"Fetched {i}/{len(urls)} pokemon")
        time.sleep(REQUEST_DELAY)

    return pd.DataFrame(rows)


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    int_cols = [
        "id", "base_experience",
        "hp", "attack", "defense", "special_attack", "special_defense",
        "speed", "total_stats",
    ]
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = ["height_m", "weight_kg"]
    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    category_cols = ["type_1", "type_2"]
    for col in category_cols:
        df[col] = df[col].astype("category")

    return df


def download_sprites(df: pd.DataFrame) -> int:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for _, row in df.head(SPRITES_LIMIT).iterrows():
        if pd.isna(row["sprite_url"]):
            continue
        path = SPRITES_DIR / f"{row['id']}_{row['name']}.png"
        try:
            response = requests.get(row["sprite_url"], timeout=TIMEOUT)
            response.raise_for_status()
            path.write_bytes(response.content)
            downloaded += 1
        except requests.RequestException as error:
            print(f"Sprite of {row['name']} is not available: {error}")

    return downloaded


def save_csv(df: pd.DataFrame, path: Path = CSV_PATH) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    df = fetch_dataset()
    df = convert_types(df)
    downloaded = download_sprites(df)
    save_csv(df)

    pd.set_option("display.max_columns", None)

    print(df.head(10))
    print(f"\nDataset size: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Collected {len(df)} of {POKEMON_LIMIT} pokemon")
    print("\nColumn dtypes:")
    print(df.dtypes.to_string())

    csv_kb = CSV_PATH.stat().st_size / 1024
    print(f"\nSaved {CSV_PATH} ({csv_kb:.1f} KB)")
    print(f"Downloaded {downloaded} sprites to {SPRITES_DIR}")
