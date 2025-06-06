import os
import pandas as pd
import time
from polygon import RESTClient  
from dotenv import load_dotenv
from datetime import datetime, timedelta

class OptionsTracker:
    def __init__(self):
        """
        Initialize the OptionsTracker class
        """
        self.client = RESTClient(os.getenv("POLYGON_API_KEY"))
        self.option_symbols = []
        self.indicators = []

        # For each time frame and each option symbol, trade status starts off False, entry price starts off 0, exit price starts off 0
        self.time_frames = ["1min", "5min", "10min"]
        self.entries = {}
        self.trades = []
    
    def get_open_price(self, symbol):
        """
        Get the open price for the symbol
        """
        # Get the open price for the symbol
        return self.client.get_daily_open_close_agg(
            symbol,
            datetime.now().strftime('%Y-%m-%d'),
            adjusted="true",
        )["open"]

    def generate_option_symbol(self, symbol, strike_price, option_type):
        """
        Generate an option symbol in standard format.
        """
        # Get today's date
        today = datetime.now()

        # Add 2 business days to today's date
        expiry_date = today + timedelta(days=2)

        # Parse the expiry date
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        
        # if expiry is a saturday, add 2 days
        if expiry.weekday() == 5:
            expiry += timedelta(days=2)
        # if expiry is a sunday, add 1 day
        elif expiry.weekday() == 6:
            expiry += timedelta(days=1)

        # Format date as YYMMDD
        date_str = expiry.strftime('%y%m%d')
        
        # Format strike price as 8-digit string with 3 decimal places
        # (multiply by 1000 to handle cents, then pad to 8 digits)
        strike_str = f"{int(strike_price * 1000):08d}"
        
        # Validate option type
        option_type = option_type.upper()
        if option_type not in ['C', 'P']:
            raise ValueError("option_type must be 'C' for call or 'P' for put")
        
        # Combine all parts: SYMBOL + YYMMDD + C/P + 8-digit strike
        option_symbol = f"{symbol.upper()}{date_str}{option_type}{strike_str}"
        
        return option_symbol

    def fetch_ohlcv(self, option_symbol):
        """
        Fetch 1 minute ohlcv for the option symbol
        """
        aggs = []
        for a in self.client.list_aggs(
            f"O:{option_symbol}",
            1,
            "day",
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%Y-%m-%d'),
            adjusted="true",
            sort="asc",
            limit=120,
        ):
            aggs.append(a)
        # Save to csv
        with open(f"{option_symbol}_1min.csv", "a") as f:
            f.write(f"{aggs[-1]["t"]},{aggs[-1]["o"]},{aggs[-1]["h"]},{aggs[-1]["l"]},{aggs[-1]["c"]},{aggs[-1]["v"]}\n")
    
    def aggregate_minute_data(self, option_symbol):
        # Read csv
        df = pd.read_csv(f"{option_symbol}_1min.csv")
        # Aggregate to 5 minutes and 10 minutes and save to csv
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        df_10min = df.resample('10min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        # Save to csv
        df_5min.to_csv(f"{option_symbol}_5min.csv", index=False)
        df_10min.to_csv(f"{option_symbol}_10min.csv", index=False)

    def calculate_indicators(self, option_symbol, time_frame):
        """
        Calculate ema_7, vwma_17, ema_12, ema_26, macd_line, macd_signal, roc_8 for new entries
        """
        for time_frame in self.time_frames:
            # Read csv
            df = pd.read_csv(f"{option_symbol}_{time_frame}.csv")
        
            # Calculate ema_7, vwma_17,ema_7,vwma_17,ema_12,ema_26,macd_line,macd_signal,roc_8 for new entries
            df["ema_7"] = df["close"].ewm(span=7, adjust=False).mean()
            df["vwma_17"] = df["close"].ewm(span=17, adjust=False).mean()
            df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
            df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
            df["macd_line"] = df["ema_12"] - df["ema_26"]
            df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
            df["roc_8"] = df["close"].pct_change(8)
            # Save to csv
            df.to_csv(f"{option_symbol}_{time_frame}.csv", index=False)


    def check_for_entry(self, option_symbol):
        for time_frame in self.time_frames: 
            # Read csv
            df = pd.read_csv(f"{option_symbol}_{time_frame}.csv")
            # Check if ema_7 is greater than vwma_17 and roc_8 is greater than 0
            if (df["ema_7"].iloc[-1] > df["vwma_17"].iloc[-1] and 
                df["roc_8"].iloc[-1] > 0 and 
                df["macd_line"].iloc[-1] > df["macd_signal"].iloc[-1] and 
                not self.entries[option_symbol][time_frame]["open"]):
                # Record the entry
                self.entries[option_symbol][time_frame]["open"] = True
                # Record the entry price
                self.entries[option_symbol][time_frame]["entry_price"] = df["close"].iloc[-1]
            
            
    def check_for_exit(self, option_symbol):
        for time_frame in self.time_frames:
            # Read csv
            df = pd.read_csv(f"{option_symbol}_{time_frame}.csv")
            # Check if any of these three are true (ema_7 is less than vwma_17, roc_8 is less than 0, macd_line is less than macd_signal)
            if (df["ema_7"].iloc[-1] < df["vwma_17"].iloc[-1] or df["roc_8"].iloc[-1] < 0 or df["macd_line"].iloc[-1] < df["macd_signal"].iloc[-1]) and self.entries[option_symbol][time_frame]["open"]:
                # Record the exit
                self.entries[option_symbol][time_frame]["open"] = False
                # Calculate profit/loss
                profit_loss = df["close"].iloc[-1] - self.entries[option_symbol][time_frame]["entry_price"]
                # Record the trade entry, exit, and profit/loss
                self.trades.append({
                    "option_symbol": option_symbol,
                    "time_frame": time_frame,
                    "entry_price": self.entries[option_symbol][time_frame]["entry_price"],
                    "exit_price": df["close"].iloc[-1],
                    "profit_loss": profit_loss
                })

                # Store the entry and exit in a csv file with profit/loss
                with open(f"{option_symbol}_{time_frame}_entry_exit.csv", "a") as f:
                    f.write(f"{option_symbol},{time_frame},{df['close'].iloc[-1]},{df['close'].iloc[-1]},{profit_loss}\n")

        
    def run(self):

        # Get strike prices
        strike_price_1 = self.get_open_price("SPY")
        strike_price_2 = strike_price_1 - 1

        # Generate option symbols
        option_symbol_1_c = self.generate_option_symbol("SPY", strike_price_1, "C")
        option_symbol_1_p = self.generate_option_symbol("SPY", strike_price_1, "P")
        option_symbol_2_c = self.generate_option_symbol("SPY", strike_price_2, "C")
        option_symbol_2_p = self.generate_option_symbol("SPY", strike_price_2, "P")

        # Create a csv file for each option symbol
        with open(f"{option_symbol_1_c}_1min.csv", "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")
        with open(f"{option_symbol_1_p}_1min.csv", "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")
        with open(f"{option_symbol_2_c}_1min.csv", "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")   
        with open(f"{option_symbol_2_p}_1min.csv", "w") as f:
            f.write("timestamp,open,high,low,close,volume\n")
        
        # At current minute and 5 seconds query fetch_ohlcv for each option symbol
        while True:
            while datetime.now().second != 5:
                # Do nothing
                pass

            # Fetch ohlcv
            self.fetch_ohlcv(option_symbol_1_c)
            self.fetch_ohlcv(option_symbol_1_p)
            self.fetch_ohlcv(option_symbol_2_c)
            self.fetch_ohlcv(option_symbol_2_p)

            # Calculate indicators
            self.calculate_indicators(option_symbol_1_c)
            self.calculate_indicators(option_symbol_1_p)
            self.calculate_indicators(option_symbol_2_c)
            self.calculate_indicators(option_symbol_2_p)

            # Check for entry
            self.check_for_entry(option_symbol_1_c)
            self.check_for_entry(option_symbol_1_p)
            self.check_for_entry(option_symbol_2_c)
            self.check_for_entry(option_symbol_2_p)

            # Check for exit
            self.check_for_exit(option_symbol_1_c)
            self.check_for_exit(option_symbol_1_p)
            self.check_for_exit(option_symbol_2_c)
            self.check_for_exit(option_symbol_2_p)
