
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

SERIES_OPTIONS = {
    "daily": ("TIME_SERIES_DAILY", "Time Series (Daily)"),
    "weekly": ("TIME_SERIES_WEEKLY", "Weekly Time Series"),
    "monthly": ("TIME_SERIES_MONTHLY", "Monthly Time Series")
}


# Load stock symbols from the CSV file
def load_stocks():
    stocks = []

    with open(
        BASE_DIR / "stocks.csv",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            symbol = row["Symbol"].strip()
            name = row["Name"].strip()

            if symbol:
                stocks.append({
                    "symbol": symbol,
                    "name": name
                })

    return sorted(stocks, key=lambda stock: stock["symbol"])


# Retrieve stock information from Alpha Vantage
def get_stock_data(symbol, time_series):
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")

    if not api_key:
        raise ValueError("Alpha Vantage API key is missing.")

    if time_series not in SERIES_OPTIONS:
        raise ValueError("Invalid time series selected.")

    function_name, data_key = SERIES_OPTIONS[time_series]

    params = {
        "function": function_name,
        "symbol": symbol,
        "apikey": api_key
    }

    if time_series == "daily":
        params["outputsize"] = "compact"

    response = requests.get(
        "https://www.alphavantage.co/query",
        params=params,
        timeout=20
    )

    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise ValueError("Invalid response from Alpha Vantage.")

    if not isinstance(data, dict):
        raise ValueError("Unexpected response from Alpha Vantage.")

    if data_key not in data:
        if "Note" in data or "Information" in data:
            raise ValueError(
                "Alpha Vantage could not provide the requested data. "
                "The API may have reached its request limit "
                "or this feature may require a paid plan."
            )

        if "Error Message" in data:
            raise ValueError("Invalid or unavailable stock symbol.")

        raise ValueError("Stock data is currently unavailable.")

    daily_data = data[data_key]

    if not isinstance(daily_data, dict) or not daily_data:
        raise ValueError("No stock data was returned.")

    df = pd.DataFrame.from_dict(daily_data, orient="index")

    if "4. close" not in df.columns:
        raise ValueError("Closing price data is missing.")

    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.loc[~df.index.isna()].copy()

    df["Close"] = pd.to_numeric(
        df["4. close"], errors="coerce"
    )

    df = df.dropna(subset=["Close"])
    df = df.sort_index()

    if df.empty:
        raise ValueError("No valid stock prices were returned.")

    return df


# Generate stock chart
def create_chart(df, symbol, chart_type, time_series):
    chart_data = df.reset_index()
    chart_data = chart_data.rename(columns={"index": "Date"})

    title = (
        f"{symbol} Stock Closing Prices "
        f"({time_series.capitalize()})"
    )

    if chart_type == "line":
        fig = px.line(
            chart_data,
            x="Date",
            y="Close",
            title=title
        )
    elif chart_type == "bar":
        fig = px.bar(
            chart_data,
            x="Date",
            y="Close",
            title=title
        )
    else:
        raise ValueError("Invalid chart type selected.")

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Closing Price (USD)",
        template="plotly_white",
        margin=dict(l=40, r=30, t=70, b=40),
        height=480
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=True
    )


# Main Flask route - GET and POST
@app.route("/", methods=["GET", "POST"])
def index():
    stocks = load_stocks()

    chart_html = None
    error = None

    selected_symbol = request.form.get("symbol", "")
    selected_chart = request.form.get("chart_type", "line")
    selected_series = request.form.get("time_series", "daily")
    selected_start = request.form.get("start_date", "")
    selected_end = request.form.get("end_date", "")

    if request.method == "POST":
        try:
            # Validate stock symbol
            valid_symbols = {
                stock["symbol"] for stock in stocks
            }

            if not selected_symbol:
                raise ValueError("Please select a stock symbol.")

            if selected_symbol not in valid_symbols:
                raise ValueError("Invalid stock symbol selected.")

            # Validate chart type
            if selected_chart not in ("line", "bar"):
                raise ValueError("Invalid chart type selected.")

            # Validate time series
            if selected_series not in SERIES_OPTIONS:
                raise ValueError("Invalid time series selected.")

            # Validate start date
            if not selected_start:
                raise ValueError("Please enter a start date.")

            try:
                start = date.fromisoformat(selected_start)
            except ValueError:
                raise ValueError("Invalid start date.")

            # Validate end date
            if not selected_end:
                raise ValueError("Please enter an end date.")

            try:
                end = date.fromisoformat(selected_end)
            except ValueError:
                raise ValueError("Invalid end date.")

            # Validate date range
            if start >= end:
                raise ValueError(
                    "End date must be after start date."
                )

            if end > date.today():
                raise ValueError(
                    "End date cannot be in the future."
                )

            # Retrieve stock prices
            df = get_stock_data(
                selected_symbol,
                selected_series
            )

            # Filter by selected dates
            df = df.loc[
                (df.index.date >= start) &
                (df.index.date <= end)
            ]

            if df.empty:
                raise ValueError(
                    "No stock data found for this date range. "
                    "Try different dates or a different time series."
                )

            # Generate chart
            chart_html = create_chart(
                df,
                selected_symbol,
                selected_chart,
                selected_series
            )

        except ValueError as e:
            error = str(e)

        except requests.RequestException:
            error = (
                "Unable to connect to Alpha Vantage. "
                "Please try again."
            )

        except (KeyError, TypeError, pd.errors.ParserError):
            error = "Unable to process the stock data."

    return render_template(
        "index.html",
        stocks=stocks,
        chart_html=chart_html,
        error=error,
        selected_symbol=selected_symbol,
        selected_chart=selected_chart,
        selected_series=selected_series,
        selected_start=selected_start,
        selected_end=selected_end
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
