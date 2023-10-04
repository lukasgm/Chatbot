import yfinance as yf
import talib
import pandas as pd
import numpy as np

# Download historical data as a pandas DataFrame
data = yf.download('^GSPC', start='2018-01-01', end='2023-07-10')

# Calculate the 14-day RSI
data['RSI'] = talib.RSI(data['Close'], timeperiod = 14)

# Define the upper and lower RSI thresholds
rsi_upper = 70
rsi_lower = 30

# Create a column to hold the trading signals
data['Signal'] = 0.0

# Generate trading signals based on the RSI thresholds
data['Signal'] = np.where(data['RSI'] > rsi_upper, -1.0, data['Signal']) 
data['Signal'] = np.where(data['RSI'] < rsi_lower, 1.0, data['Signal'])

# Generate trading orders based on the signals
data['Position'] = data['Signal'].diff()

print(data)
