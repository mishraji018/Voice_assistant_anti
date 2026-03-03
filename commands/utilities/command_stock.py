import yfinance as yf
from core.audio.voice_utils import speak

def get_stock_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        # Try multiple keys since yfinance API changes over versions
        price = (info.get('currentPrice')
                 or info.get('regularMarketPrice')
                 or info.get('previousClose'))
        if price:
            speak(f"The current price of {symbol.upper()} is {price} dollars.")
        else:
            speak(f"Could not find price for {symbol.upper()}.")
    except Exception:
        speak("Failed to fetch stock price.")
