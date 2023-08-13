"""
This script determines which stocks / ETFs to sell to make a given taxable profit.
Usually that taxable profit is the amount of the Sparerpauschbetrag that is left.
To keep brokerage fees low,
1. the amount of trades should be minimized
2. within solutions with the same amount of trades, the volume of the trades should be minimized
This optimization problem is solved using backtracking.
"""

import argparse
import json
from typing import Any, Optional

MAX_TRADES = 3
INFINITY = 1_000_000_000


def determine_optimal_sales(input_file: str, prices_file: str, desired_profit: float) -> None:
    """
    Determine the optimal sales to make to maximize the tax-free amount.
    """
    with open(input_file) as input_file_handle, open(prices_file) as prices_file_handle:
        data = json.load(input_file_handle)
        current_prices = json.load(prices_file_handle)
    fifo_holdings = get_fifo_holdings(data)
    teilfreistellung = {symbol: symbol_data["teilfreistellung"] for symbol, symbol_data in data.items()}
    symbols = list(fifo_holdings.keys())

    # backtracking solver trying to reach the profit goal with the least amount of trades and lowest volume
    def _backtrack(
        allowed_trades: int,
        index: int,
        profit_left: float,
        partial_solution: list[dict[str, Any]]
    ) -> Optional[tuple[float, list[dict[str, Any]]]]:
        if index > len(symbols) or allowed_trades <= 0:
            return None
        best_volume = INFINITY
        best_solution = []
        for offset, symbol in enumerate(symbols[index:]):
            symbol_index = index + offset
            # try to use the current symbol
            current_buy_value, current_amount = 0, 0
            for i in range(0, len(fifo_holdings[symbol])):
                # try selling more and more of the current symbol
                last_amount = fifo_holdings[symbol][i]["amount"]
                current_buy_value += last_amount * fifo_holdings[symbol][i]["unit_price"]
                current_amount += last_amount
                if current_buy_value / current_amount < current_prices[symbol]:
                    # we can make a profit
                    volume = current_amount * current_prices[symbol]
                    profit = volume - current_buy_value
                    taxable_profit = profit * (1 - teilfreistellung[symbol])
                    last_buy_profit = last_amount * (current_prices[symbol] - fifo_holdings[symbol][i]["unit_price"])
                    partial_solution.append({
                        "symbol": symbol,
                        "amount": current_amount,
                        "profit": profit,
                        "taxable_profit": profit * (1 - teilfreistellung[symbol]),
                        "volume": volume,
                        "last_buy_amount": last_amount,
                        "last_buy_profit": last_buy_profit,
                        "last_buy_taxable_profit": last_buy_profit * (1 - teilfreistellung[symbol]),
                        "last_buy_volume": last_amount * current_prices[symbol],
                    })
                    if taxable_profit >= profit_left:
                        # found solution, reduce the volume of the trade where the volume reduction is the highest
                        difference = taxable_profit - profit_left
                        refined_solution = refine_solution(partial_solution, difference)
                        total_volume = sum([solution_trade["volume"] for solution_trade in refined_solution])
                        return total_volume, refined_solution

                    # we need more taxable profit, try to continue with the next key
                    if allowed_trades > 1:
                        rec = _backtrack(allowed_trades - 1, symbol_index + 1, profit_left - taxable_profit, partial_solution)
                        if rec:
                            rec_volume, rec_solution = rec
                            if rec_volume < best_volume:
                                best_volume, best_solution = rec_volume, rec_solution
                    # undo of the last step
                    partial_solution.pop()
        # we tried all keys
        if best_volume < INFINITY:
            return best_volume, best_solution
        else:
            return None

    # try to find a solution with the least amount of trades
    for number_of_allowed_trades in range(1, MAX_TRADES + 1):
        maybe_solution = _backtrack(number_of_allowed_trades, 0, desired_profit, [])
        if maybe_solution:
            solution_volume, solution = maybe_solution
            print(f"Solution found with {number_of_allowed_trades} trades and volume {solution_volume}€:")
            for trade in solution:
                print(f"{trade['symbol']}: Sell {trade['amount']} pieces at {current_prices[trade['symbol']]}€ (volume"
                      f" {trade['volume']}) for a profit of {trade['profit']}€ ({trade['taxable_profit']} taxable)")
            break
    else:
        print(f"No solution found with up to {MAX_TRADES} trades.")


def refine_solution(solution: list[dict[str, Any]], difference: float) -> list[dict[str, Any]]:
    """
    Reduce the volume of the trade where the volume reduction is the highest, to make difference less profit.
    """
    refined_solution = solution.copy()
    best_volume_reduction, best_proportion, best_id = 0, 0, -1
    for trade_index, trades in enumerate(solution):
        if trades["last_buy_taxable_profit"] > difference:
            profit_proportion_not_needed = difference / trades["last_buy_taxable_profit"]
            volume_reduction = profit_proportion_not_needed * trades["last_buy_volume"]
            if volume_reduction > best_volume_reduction:
                best_volume_reduction = volume_reduction
                best_id = trade_index
                best_proportion = profit_proportion_not_needed
    for update_key in ["amount", "profit", "taxable_profit", "volume"]:
        refined_solution[best_id][update_key] -= solution[best_id][f"last_buy_{update_key}"] * best_proportion
        refined_solution[best_id][f"last_buy_{update_key}"] *= (1 - best_proportion)
    return refined_solution


def get_fifo_holdings(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    Returns a dict with the current holdings for each symbol in FIFO order.
    """
    fifo_holdings = {}
    for symbol, symbol_data in data.items():
        fifo_holdings[symbol] = []
        for trade in symbol_data["trades"]:
            if trade["type"] == "buy":
                fifo_holdings[symbol].append(trade)
            elif trade["type"] == "sell":
                for i, holding in enumerate(fifo_holdings[symbol]):
                    if holding["amount"] > trade["amount"]:
                        holding["amount"] -= trade["amount"]
                        break
                    else:
                        trade["amount"] -= holding["amount"]
                        fifo_holdings[symbol][i] = None
                fifo_holdings[symbol] = [h for h in fifo_holdings[symbol] if h is not None]
        if len(fifo_holdings[symbol]) == 0:
            del fifo_holdings[symbol]
    return fifo_holdings


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input-file",
        type=str,
        default="data/dkb.json",
        help="JSON file containing trade data",
    )
    parser.add_argument(
        "-p",
        "--prices-file",
        type=str,
        default="data/current_prices.json",
        help="JSON file containing current prices",
    )
    parser.add_argument(
        "-d",
        "--desired-profit",
        type=float,
        default=1000.0,
        help="Desired profit in EUR",
    )
    args = parser.parse_args()
    determine_optimal_sales(args.input_file, args.prices_file, args.desired_profit)