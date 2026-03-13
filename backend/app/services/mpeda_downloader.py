"""
MPEDA Data Downloader Service
Downloads marine export data from MPEDA website periodically
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

MPEDA_DOWNLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "mpeda"
MPEDA_URLS = {
    "item": "https://mpeda.gov.in/wp-content/uploads/2025/12/ITEM_WISE_EXPORT_DATA_10_YEARS-24-25.xlsx",
    "market": "https://mpeda.gov.in/wp-content/uploads/2025/12/MARKET_WISE_EXPORT_DATA_10_YEARS-24-25.xlsx",
    "port": "https://mpeda.gov.in/wp-content/uploads/2025/12/PORT_WISE_EXPORT_DATA_10_YEARS-24-25.xlsx",
}


def ensure_download_dir():
    """Ensure the download directory exists."""
    MPEDA_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def download_mpeda_data(data_type: str = "item") -> pd.DataFrame | None:
    """
    Download MPEDA Excel data.

    Args:
        data_type: One of 'item', 'market', 'port'

    Returns:
        DataFrame with the downloaded data
    """
    if data_type not in MPEDA_URLS:
        raise ValueError(
            f"Invalid data_type: {data_type}. Must be one of {list(MPEDA_URLS.keys())}"
        )

    url = MPEDA_URLS[data_type]
    filename = f"{data_type}_wise_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filepath = MPEDA_DOWNLOAD_DIR / filename

    ensure_download_dir()

    try:
        logger.info(f"Downloading MPEDA {data_type} data from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        logger.info(f"Downloaded to {filepath}")

        df = pd.read_excel(filepath)
        return df

    except requests.RequestException as e:
        logger.error(f"Failed to download MPEDA data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing MPEDA data: {e}")
        return None


def download_all_mpeda_data() -> dict[str, pd.DataFrame | None]:
    """Download all MPEDA data types."""
    results = {}
    for data_type in MPEDA_URLS.keys():
        results[data_type] = download_mpeda_data(data_type)
    return results


def get_latest_downloaded_file(data_type: str) -> Path | None:
    """Get the most recently downloaded file for a data type."""
    if not MPEDA_DOWNLOAD_DIR.exists():
        return None

    pattern = f"{data_type}_wise_export_*.xlsx"
    files = list(MPEDA_DOWNLOAD_DIR.glob(pattern))

    if not files:
        return None

    return max(files, key=lambda f: f.stat().st_mtime)


def load_latest_data(data_type: str) -> pd.DataFrame | None:
    """Load the most recently downloaded data."""
    latest_file = get_latest_downloaded_file(data_type)

    if latest_file is None:
        logger.warning(f"No downloaded file found for {data_type}")
        return None

    try:
        df = pd.read_excel(latest_file)
        logger.info(f"Loaded {len(df)} rows from {latest_file.name}")
        return df
    except Exception as e:
        logger.error(f"Error loading {latest_file}: {e}")
        return None


def parse_item_wise_data(df: pd.DataFrame) -> list[dict]:
    """
    Parse item-wise export data into standardized format.

    Returns list of records with:
    - commodity: item name
    - year: financial year
    - quantity_mt: quantity in metric tons
    - value_crore: value in Rs. Crore
    """
    records = []

    header_row = df.iloc[1]
    years = []
    for col_idx in range(2, len(header_row)):
        year = header_row.iloc[col_idx]
        if pd.notna(year):
            years.append(str(year))

    current_commodity = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        first_cell = row.iloc[0]
        row_type = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""

        if row_type == "Q:":
            current_commodity = (
                str(first_cell) if pd.notna(first_cell) else current_commodity
            )
            for col_idx in range(2, len(row)):
                if col_idx - 2 < len(years):
                    try:
                        value = (
                            float(row.iloc[col_idx])
                            if pd.notna(row.iloc[col_idx])
                            else 0
                        )
                        if value > 0:
                            records.append(
                                {
                                    "commodity": current_commodity,
                                    "year": years[col_idx - 2],
                                    "quantity_mt": value,
                                    "source": "MPEDA",
                                    "updated_at": datetime.now().isoformat(),
                                }
                            )
                    except (ValueError, IndexError):
                        continue

        elif row_type == "V:" and current_commodity:
            for col_idx in range(2, len(row)):
                if col_idx - 2 < len(years):
                    try:
                        value = (
                            float(row.iloc[col_idx])
                            if pd.notna(row.iloc[col_idx])
                            else 0
                        )
                        if value > 0:
                            year = years[col_idx - 2]
                            existing = next(
                                (
                                    r
                                    for r in records
                                    if r["commodity"] == current_commodity
                                    and r["year"] == year
                                ),
                                None,
                            )
                            if existing:
                                existing["value_crore"] = value
                            else:
                                records.append(
                                    {
                                        "commodity": current_commodity,
                                        "year": year,
                                        "value_crore": value,
                                        "source": "MPEDA",
                                        "updated_at": datetime.now().isoformat(),
                                    }
                                )
                    except (ValueError, IndexError):
                        continue

    return records


def parse_market_wise_data(df: pd.DataFrame) -> list[dict]:
    """Parse market-wise export data."""
    records = []

    for _, row in df.iterrows():
        market = row.iloc[0]
        if pd.isna(market) or market == "Market":
            continue

        years = [
            "2015-16",
            "2016-17",
            "2017-18",
            "2018-19",
            "2019-20",
            "2020-21",
            "2021-22",
            "2022-23",
            "2023-24",
            "2024-25",
        ]

        for i, year in enumerate(years):
            try:
                q_col = i * 3
                v_col = i * 3 + 1

                quantity = float(row.iloc[q_col]) if pd.notna(row.iloc[q_col]) else 0
                value = float(row.iloc[v_col]) if pd.notna(row.iloc[v_col]) else 0

                if quantity > 0 or value > 0:
                    records.append(
                        {
                            "destination": str(market),
                            "year": year,
                            "quantity_mt": quantity,
                            "value_crore": value,
                            "source": "MPEDA",
                            "updated_at": datetime.now().isoformat(),
                        }
                    )
            except (ValueError, IndexError):
                continue

    return records


def parse_port_wise_data(df: pd.DataFrame) -> list[dict]:
    """Parse port-wise export data."""
    records = []

    for _, row in df.iterrows():
        port = row.iloc[0]
        if pd.isna(port) or port == "Ports":
            continue

        years = [
            "2015-16",
            "2016-17",
            "2017-18",
            "2018-19",
            "2019-20",
            "2020-21",
            "2021-22",
            "2022-23",
            "2023-24",
            "2024-25",
        ]

        for i, year in enumerate(years):
            try:
                q_col = i * 3
                v_col = i * 3 + 1

                quantity = float(row.iloc[q_col]) if pd.notna(row.iloc[q_col]) else 0
                value = float(row.iloc[v_col]) if pd.notna(row.iloc[v_col]) else 0

                if quantity > 0 or value > 0:
                    records.append(
                        {
                            "port": str(port),
                            "year": year,
                            "quantity_mt": quantity,
                            "value_crore": value,
                            "source": "MPEDA",
                            "updated_at": datetime.now().isoformat(),
                        }
                    )
            except (ValueError, IndexError):
                continue

    return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Downloading MPEDA data...")
    results = download_all_mpeda_data()

    for data_type, df in results.items():
        if df is not None:
            print(f"\n{data_type.upper()} data: {len(df)} rows")
            print(df.head())
