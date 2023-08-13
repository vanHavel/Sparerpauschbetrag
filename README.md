# Purpose
This project determines which stocks / ETFs to sell to make a given taxable profit.
Usually that taxable profit is the amount of the Sparerpauschbetrag that is left to fill.

To keep brokerage fees low,
1. the amount of trades should be minimized
2. within solutions with the same amount of trades, the volume of the trades should be minimized

This optimization problem is solved using backtracking.

# Usage

Install the dependencies:
```
poetry install
poetry shell
```

Run the script:
```
python3 scripts/determine_optimal_sales.py
```

# Arguments
| Flag | Description |
|------| --- |
| -d   | The desired taxable profit |
| -i   | Path to the input file containing trade data (see `data/sample_trades.json` for an example) |
 | -p   | Path to the input file containing current prices for all symbols (see `data/sample_prices.json` for an example) |

# Collecting trade data

## DKB
Unfortunately, DKB does not provide an API or export to access trade data. You need to download the individual PDFs for each trade from the website.

A script `scripts/dkb_trade_data.py` is provided to parse buy / sale trades from the PDFs.
