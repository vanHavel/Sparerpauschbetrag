"""
This script extracts trade data from DKB PDFs and saves it to a JSON file.
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any

from pypdf import PdfReader

date_regex = re.compile(r"Schlusstag\s+(\d{2}\.\d{2}\.\d{4})")
date_time_regex = re.compile(r"Schlusstag/-Zeit\s+(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})")
wkn_regex = re.compile(r"\((\w{6})\)")
pieces_regex = re.compile(r"Stück\s+(\d+)(?:,(\d+))?")
price_regex = re.compile(r"Ausführungskurs\s+(\d+),(\d+)\s+EUR")


def generate_dkb_trade_data(input_directory: str, output_file: str, merge: bool) -> None:
    """
    Extracts trade data from DKB PDFs and saves it to a JSON file.
    """
    if merge and os.path.exists(output_file):
        with open(output_file) as f:
            symbols = json.load(f)
    else:
        symbols = {}
    for file in os.listdir(input_directory):
        joined_path = os.path.join(input_directory, file)
        if file.endswith(".pdf"):
            if file.startswith("Kauf_") and "Wertpapierabrechnung" in file:
                trade_type = "buy"
            elif file.startswith("Verkauf_") and "Wertpapierabrechnung" in file:
                trade_type = "sell"
            else:
                print(f"Skipping {joined_path}...")
                continue
            print(f"Processing {joined_path}...")
            pdf = PdfReader(joined_path)
            text = pdf.pages[0].extract_text()
            trade = parse_trade_data(text)
            trade["type"] = trade_type
            symbol = trade.pop("symbol")
            if symbol not in symbols:
                symbols[symbol] = {"teilfreistellung": trade["teilfreistellung"], "trades": []}
                print(f"Added {symbol} to symbols with teilfreistellung {trade['teilfreistellung']}")
            del trade["teilfreistellung"]
            for existing_trade in symbols[symbol]["trades"]:
                if existing_trade["timestamp"] == trade["timestamp"]:
                    print(f"Skipping duplicate trade on {trade['timestamp']} to {symbol}...")
                    break
            else:
                symbols[symbol]["trades"].append(trade)
                print(f"Added trade on {trade['timestamp']} to {symbol}")

    symbols = normalize_data(symbols)

    with open(output_file, "w") as f:
        json.dump(symbols, f, indent=2, sort_keys=True)


def parse_trade_data(text: str) -> dict[str, Any]:
    wkn = re.search(wkn_regex, text).group(1)
    date_and_time = re.search(date_time_regex, text)
    if date_and_time:
        parsed_datetime = datetime.strptime(date_and_time.group(1), "%d.%m.%Y %H:%M:%S")
    else:
        date = re.search(date_regex, text).group(1)
        parsed_datetime = datetime.strptime(date, "%d.%m.%Y") + timedelta(hours=23, minutes=59, seconds=59)
    pieces = re.search(pieces_regex, text)
    parsed_pieces = float(pieces.group(1)) + (float(f"0.{pieces.group(2)}") if pieces.group(2) else 0)
    price = re.search(price_regex, text)
    parsed_price = float(price.group(1)) + (float(f"0.{price.group(2)}") if price.group(2) else 0)
    return {
        "timestamp": parsed_datetime.isoformat(),
        "amount": parsed_pieces,
        "unit_price": parsed_price,
        "symbol": wkn,
        "teilfreistellung": 0.3 if "ETF" in text else 0,
    }


def normalize_data(symbols: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for symbol, symbol_data in symbols.items():
        normalized[symbol] = symbol_data
        normalized[symbol]["trades"] = list(sorted(symbol_data["trades"], key=lambda t: t["timestamp"]))
    return normalized


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input-directory",
        type=str,
        default="input/dkb",
        help="Directory containing DKB trade data PDFs",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        default="data/dkb.json",
        help="Output file for DKB trade data",
    )
    parser.add_argument(
        "-m",
        "--merge",
        action="store_true",
        help="Merge with existing data",
    )
    args = parser.parse_args()
    generate_dkb_trade_data(args.input_directory, args.output_file, args.merge)
