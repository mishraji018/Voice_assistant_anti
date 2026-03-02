import yfinance as yf
from voice_utils import speak

def get_stock_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        price = stock.info['regularMarketPrice']
        speak(f"The current price of {symbol.upper()} is {price} dollars.")
    except Exception:
        speak("Failed to fetch stock price.")
