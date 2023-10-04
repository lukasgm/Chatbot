import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# Download historical data as a pandas DataFrame
data = yf.download('^GSPC', start='2018-01-01', end='2023-07-10')

# Calculate the 50-day SMA
data['SMA_50'] = data['Close'].rolling(window=50).mean()

# Calculate the 200-day SMA
data['SMA_200'] = data['Close'].rolling(window=200).mean()

# Plot the close price, the 50-day SMA, and the 200-day SMA
data[['Close', 'SMA_50', 'SMA_200']].plot(grid=True, figsize=(10, 5))

plt.show()
