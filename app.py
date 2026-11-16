import csv
import os
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv() 

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent


def load_stocks():
    stocks = []

    with open(BASE_DIR / "stocks.csv", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            stocks.append({
                "symbol": row["Symbol"].strip(),
                "name": row["Name"].strip()
            })

    return sorted(stocks, key=lambda stock: stock["symbol"])


def get_stock_data(symbol):
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")

    if not api_key:
        raise ValueError("Alpha Vantage API key is missing.")

    url = "https://www.alphavantage.co/query"

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",
        "apikey": api_key
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if "Time Series (Daily)" not in data:
        raise ValueError(
            "Stock data unavailable. Check the stock symbol "
            "or your Alpha Vantage API limit."
        )

    daily_data = data["Time Series (Daily)"]

    df = pd.DataFrame.from_dict(daily_data, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df["Close"] = pd.to_numeric(df["4. close"])

    return df


@app.route("/", methods=["GET", "POST"])
def index():
    stocks = load_stocks()
    chart_html = None
    error = None

    if request.method == "POST":
        symbol = request.form.get("symbol", "")
        chart_type = request.form.get("chart_type", "line")
        start_date = request.form.get("start_date", "")
        end_date = request.form.get("end_date", "")

        try:
            valid_symbols = {stock["symbol"] for stock in stocks}

            if symbol not in valid_symbols:
                raise ValueError("Please select a valid stock.")

            if chart_type not in ("line", "bar"):
                raise ValueError("Invalid chart type.")

            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            if start > end:
                raise ValueError("Start date must be before end date.")

            df = get_stock_data(symbol)

            df = df.loc[
                (df.index.date >= start) &
                (df.index.date <= end)
            ]

            if df.empty:
                raise ValueError(
                    "No stock data found for these dates. "
                    "Try a more recent date range."
                )

            if chart_type == "bar":
                fig = px.bar(
                    df,
                    x=df.index,
                    y="Close",
                    title=f"{symbol} Stock Closing Prices"
                )
            else:
                fig = px.line(
                    df,
                    x=df.index,
                    y="Close",
                    title=f"{symbol} Stock Closing Prices"
                )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Closing Price (USD)",
                template="plotly_white"
            )

            chart_html = fig.to_html(
                full_html=False,
                include_plotlyjs=True
            )

        except (ValueError, requests.RequestException) as e:
            error = str(e)

    
    return render_template(
        "index.html",
        stocks=stocks,
        chart_html=chart_html,
        error=error,
        selected_symbol=request.form.get("symbol", ""),
        selected_chart=request.form.get("chart_type", "line"),
        selected_start=request.form.get("start_date", ""),
        selected_end=request.form.get("end_date", "")
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
