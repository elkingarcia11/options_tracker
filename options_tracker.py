import os
import pandas as pd
import time
from datetime import datetime, timedelta
from email_notifier import OptionsEmailNotifier
from polygon import RESTClient  
from dotenv import load_dotenv

class OptionsTracker:
    def __init__(self):
        """
        Initialize the OptionsTracker class
        """
        # Load environment variables
        load_dotenv()

        # Initialize the client
        self.client = RESTClient(os.getenv("POLYGON_API_KEY"))
        self.option_symbols = []
        self.indicators = []

        # Initialize email notifier
        self.email_notifier = OptionsEmailNotifier()

        # For each time frame and each option symbol, trade status starts off False, entry price starts off 0, exit price starts off 0
        self.time_frames = ["1min", "5min", "10min"]
        self.entries = {}
        self.trades = []
    
    def initialize_entries(self, option_symbols):
        """
        Initialize the entries structure for all option symbols and timeframes
        """
        for option_symbol in option_symbols:
            self.entries[option_symbol] = {}
            for time_frame in self.time_frames:
                self.entries[option_symbol][time_frame] = {
                    "open": False,
                    "entry_price": 0,
                    "exit_price": 0
                }
    
    def get_open_price(self, symbol):
        """
        Get the open price for the symbol, rounded to the nearest whole number
        """
        # Get the open price for the symbol and round to nearest whole number
        open_price = self.client.get_daily_open_close_agg(
            symbol,
            datetime.now().strftime('%Y-%m-%d'),
            adjusted="true",
        )["open"]
        
        return round(open_price)

    def generate_option_symbol(self, symbol, strike_price, option_type):
        """
        Generate an option symbol in standard format.
        """
        # Get today's date
        today = datetime.now()

        # Add 2 business days to today's date
        expiry_date = today + timedelta(days=2)

        # Check if expiry is a weekend and adjust
        if expiry_date.weekday() == 5:  # Saturday
            expiry_date += timedelta(days=2)
        elif expiry_date.weekday() == 6:  # Sunday
            expiry_date += timedelta(days=1)

        # Format date as YYMMDD
        date_str = expiry_date.strftime('%y%m%d')
        
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
        Fetch 1 minute ohlcv for the option symbol.
        If file is empty, fetch all available data.
        If file exists, fetch from last timestamp onwards.
        """
        csv_filename = f"{option_symbol}_1min.csv"
        
        # Check if file exists and is not empty
        file_exists = os.path.exists(csv_filename)
        is_empty = True
        last_timestamp = None
        
        if file_exists:
            try:
                # Check if file has content beyond header
                with open(csv_filename, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # More than just header
                        is_empty = False
                        # Get the last timestamp from the file
                        last_line = lines[-1].strip()
                        if last_line:
                            last_timestamp = int(last_line.split(',')[0])
            except Exception as e:
                print(f"Error reading existing file {csv_filename}: {e}")
                is_empty = True
        
        # Determine the correct trading date
        def get_trading_date():
            now = datetime.now()
            # Convert to ET timezone (approximate - doesn't handle DST perfectly)
            import pytz
            try:
                et = pytz.timezone('US/Eastern')
                now_et = now.astimezone(et)
            except:
                # Fallback if pytz not available - assume EST (UTC-5)
                now_et = now - timedelta(hours=5)
            
            # Check if it's a weekday (0=Monday, 6=Sunday)
            if now_et.weekday() < 5:  # Monday-Friday
                # Check if it's after 9:30 AM ET
                market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                if now_et >= market_open:
                    return now_et.strftime('%Y-%m-%d')
            
            # Find the last valid trading day (previous weekday)
            days_back = 1
            while True:
                candidate_date = now_et - timedelta(days=days_back)
                if candidate_date.weekday() < 5:  # It's a weekday
                    return candidate_date.strftime('%Y-%m-%d')
                days_back += 1
                if days_back > 7:  # Safety check
                    break
            
            # Fallback to yesterday if something goes wrong
            return (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Determine date range for fetching data
        if is_empty:
            # Fetch all data from past week to ensure we get sufficient historical data
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            to_date = get_trading_date()
            print(f"📥 Fetching all OHLCV data for {option_symbol} from {from_date} to {to_date}")
        else:
            # Fetch data from last timestamp onwards
            # Convert last timestamp to date (add small buffer to ensure we don't miss data)
            from_timestamp = datetime.fromtimestamp(last_timestamp / 1000)
            from_date = from_timestamp.strftime('%Y-%m-%d')
            to_date = get_trading_date()
            print(f"📈 Fetching incremental OHLCV data for {option_symbol} from {from_date} to {to_date}")
        
        # Fetch data from API
        aggs = []
        try:
            for a in self.client.list_aggs(
                f"O:{option_symbol}",
                1,
                "minute",  # Changed from "day" to "minute" for 1-minute data
                from_date,
                to_date,
                adjusted="true",
                sort="asc",
                limit=50000,  # Increased limit to get more historical data
            ):
                # Skip data that we already have (if incremental update)
                if not is_empty and last_timestamp and a['t'] <= last_timestamp:
                    continue
                aggs.append(a)
        except Exception as e:
            print(f"❌ Error fetching data for {option_symbol}: {e}")
            return
        
        if not aggs:
            print(f"⚠️  No new data available for {option_symbol}")
            return
            
        # Save to csv
        mode = 'w' if is_empty else 'a'  # Write mode if empty (includes header), append if not
        with open(csv_filename, mode) as f:
            # Write header only if file is empty/new
            if is_empty:
                f.write("timestamp,open,high,low,close,volume\n")
            
            # Write all fetched data
            for agg in aggs:
                f.write(f"{agg['t']},{agg['o']},{agg['h']},{agg['l']},{agg['c']},{agg['v']}\n")
        
        print(f"✅ Added {len(aggs)} new OHLCV records for {option_symbol}")

    def aggregate_minute_data(self, option_symbol):
        # Read csv
        df = pd.read_csv(f"{option_symbol}_1min.csv")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Aggregate to 5 minutes
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        # Aggregate 10 minutes
        df_10min = df.resample('10min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Save to csv
        df_5min.to_csv(f"{option_symbol}_5min.csv")
        df_10min.to_csv(f"{option_symbol}_10min.csv")

    def calculate_indicators(self, option_symbol, time_frame):
        """
        Calculate ema_7, vwma_17, ema_12, ema_26, macd_line, macd_signal, roc_8 for new entries
        """
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
                entry_price = df["close"].iloc[-1]
                self.entries[option_symbol][time_frame]["entry_price"] = entry_price
                
                # Send email notification for entry
                signal_details = {
                    'ema_vwma': df["ema_7"].iloc[-1] > df["vwma_17"].iloc[-1],
                    'roc_positive': df["roc_8"].iloc[-1] > 0,
                    'macd_bullish': df["macd_line"].iloc[-1] > df["macd_signal"].iloc[-1]
                }
                
                self.email_notifier.send_trade_notification(
                    option_symbol=option_symbol,
                    timeframe=time_frame,
                    action='ENTRY',
                    price=entry_price,
                    signal_details=signal_details
                )
                
                print(f"✅ ENTRY: {option_symbol} ({time_frame}) at ${entry_price:.4f}")
            
            
    def check_for_exit(self, option_symbol):
        for time_frame in self.time_frames:
            # Read csv
            df = pd.read_csv(f"{option_symbol}_{time_frame}.csv")
            
            # Check individual exit conditions
            condition1 = df["ema_7"].iloc[-1] < df["vwma_17"].iloc[-1]  # EMA(7) < VWMA(17)
            condition2 = df["roc_8"].iloc[-1] < 0                      # ROC(8) < 0
            condition3 = df["macd_line"].iloc[-1] < df["macd_signal"].iloc[-1]  # MACD Line < MACD Signal
            
            # Count how many conditions are true
            exit_conditions_met = sum([condition1, condition2, condition3])
            
            # Exit if at least 2 out of 3 conditions are true AND we have an open position
            if exit_conditions_met >= 2 and self.entries[option_symbol][time_frame]["open"]:
                # Record the exit
                self.entries[option_symbol][time_frame]["open"] = False
                
                # Calculate profit/loss
                entry_price = self.entries[option_symbol][time_frame]["entry_price"]
                exit_price = df["close"].iloc[-1]
                profit_loss = exit_price - entry_price
                
                # Record the trade entry, exit, and profit/loss
                self.trades.append({
                    "option_symbol": option_symbol,
                    "time_frame": time_frame,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "profit_loss": profit_loss
                })

                # Store the entry and exit in a csv file with profit/loss
                with open(f"{option_symbol}_{time_frame}_entry_exit.csv", "a") as f:
                    f.write(f"{option_symbol},{time_frame},{entry_price},{exit_price},{profit_loss}\n")

                # Send email notification for exit
                signal_details = {
                    'conditions_met': exit_conditions_met,
                    'ema_vwma_bearish': condition1,
                    'roc_negative': condition2,
                    'macd_bearish': condition3
                }
                
                pnl_info = {
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss
                }
                
                self.email_notifier.send_trade_notification(
                    option_symbol=option_symbol,
                    timeframe=time_frame,
                    action='EXIT',
                    price=exit_price,
                    signal_details=signal_details,
                    pnl_info=pnl_info
                )
                
                pnl_status = "PROFIT" if profit_loss >= 0 else "LOSS"
                print(f"🔚 EXIT: {option_symbol} ({time_frame}) at ${exit_price:.4f} - {pnl_status}: ${profit_loss:.4f}")

        
    def run(self):
        # Get strike prices
        strike_price_1 = self.get_open_price("SPY")
        strike_price_2 = strike_price_1 - 1

        # Generate option symbols
        option_symbol_1_c = self.generate_option_symbol("SPY", strike_price_1, "C")
        option_symbol_1_p = self.generate_option_symbol("SPY", strike_price_1, "P")
        option_symbol_2_c = self.generate_option_symbol("SPY", strike_price_2, "C")
        option_symbol_2_p = self.generate_option_symbol("SPY", strike_price_2, "P")

        # Initialize entries structure
        option_symbols = [option_symbol_1_c, option_symbol_1_p, option_symbol_2_c, option_symbol_2_p]
        self.initialize_entries(option_symbols)

        # Fetch ohlcv - the method now handles file creation and incremental updates
        self.fetch_ohlcv(option_symbol_1_c)
        self.fetch_ohlcv(option_symbol_1_p)
        self.fetch_ohlcv(option_symbol_2_c)
        self.fetch_ohlcv(option_symbol_2_p)

        # Aggregate minute data to create 5min and 10min timeframes
        self.aggregate_minute_data(option_symbol_1_c)
        self.aggregate_minute_data(option_symbol_1_p)
        self.aggregate_minute_data(option_symbol_2_c)
        self.aggregate_minute_data(option_symbol_2_p)

        # Calculate indicators for each timeframe
        for time_frame in self.time_frames:
            self.calculate_indicators(option_symbol_1_c, time_frame)
            self.calculate_indicators(option_symbol_1_p, time_frame)
            self.calculate_indicators(option_symbol_2_c, time_frame)
            self.calculate_indicators(option_symbol_2_p, time_frame)

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




if __name__ == "__main__":
    tracker = OptionsTracker()
    tracker.run()
