import os
import pandas as pd
import time
from datetime import datetime, timedelta
from polygon import RESTClient  
from dotenv import load_dotenv

class OptionsTracker:
    def __init__(self):
        """
        Initialize the OptionsTracker class
        """
        # Load environment variables
        load_dotenv()

        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)

        # Initialize the client
        self.client = RESTClient(os.getenv("POLYGON_API_KEY"))

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
    
    def get_open_price(self, symbol, date):
        """
        Get the open price for the symbol on a specific date (no rounding)
        """
        # Get the open price for the symbol (preserve exact value)
        response = self.client.get_daily_open_close_agg(
            symbol,
            date,
            adjusted="true",
        )
        open_price = response.open
        
        return open_price

    def fetch_ohlcv(self, option_symbol, start_date, end_date):
        """
        Fetch 1 minute ohlcv for the option symbol between start and end dates.
        """
        csv_filename = f"data/{option_symbol}_1min.csv"
        
        # Always fetch fresh data for backtesting
        print(f"📥 Fetching OHLCV data for {option_symbol} from {start_date} to {end_date}")
        
        # Fetch data from API for the date range
        aggs = []
        try:
            for a in self.client.list_aggs(
                f"O:{option_symbol}",
                1,
                "minute",
                start_date,
                end_date,
                adjusted="true",
                sort="asc",
                limit=50000,
            ):
                aggs.append(a)
        except Exception as e:
            print(f"❌ Error fetching data for {option_symbol}: {e}")
            return
        
        if not aggs:
            print(f"⚠️  No data available for {option_symbol} from {start_date} to {end_date}")
            return
            
        # Save to csv (overwrite existing data)
        with open(csv_filename, 'w') as f:
            # Write header
            f.write("timestamp,open,high,low,close,volume\n")
            
            # Write all fetched data (no rounding)
            for agg in aggs:
                f.write(f"{agg.timestamp},{agg.open},{agg.high},{agg.low},{agg.close},{agg.volume}\n")
        
        print(f"✅ Saved {len(aggs)} OHLCV records for {option_symbol}")

    def aggregate_minute_data(self, option_symbol):
        # Read csv
        df = pd.read_csv(f"data/{option_symbol}_1min.csv")
        
        # Convert timestamp from milliseconds to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Remove rows with NaN values (in case resampling creates empty periods)
        df = df.dropna()
        
        if len(df) == 0:
            print(f"⚠️  No valid data to aggregate for {option_symbol}")
            return
        
        # Aggregate to 5 minutes
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()  # Remove empty periods
        
        # Aggregate 10 minutes  
        df_10min = df.resample('10min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()  # Remove empty periods
        
        # Save to csv
        df_5min.to_csv(f"data/{option_symbol}_5min.csv")
        df_10min.to_csv(f"data/{option_symbol}_10min.csv")
        
        print(f"📊 Aggregated {len(df)} 1min → {len(df_5min)} 5min → {len(df_10min)} 10min candles for {option_symbol}")

    def calculate_indicators(self, option_symbol, time_frame):
        """
        Calculate ema_7, vwma_17, ema_12, ema_26, macd_line, macd_signal, roc_8 for new entries
        """
        # Read csv
        df = pd.read_csv(f"data/{option_symbol}_{time_frame}.csv")
    
        # Calculate ema_7, vwma_17,ema_7,vwma_17,ema_12,ema_26,macd_line,macd_signal,roc_8 for new entries
        df["ema_7"] = df["close"].ewm(span=7, adjust=False).mean()
        df["vwma_17"] = df["close"].ewm(span=17, adjust=False).mean()
        df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
        df["macd_line"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
        df["roc_8"] = df["close"].pct_change(8)
        # Save to csv
        df.to_csv(f"data/{option_symbol}_{time_frame}.csv", index=False)


    def check_for_entry(self, option_symbol):
        for time_frame in self.time_frames: 
            # Read csv
            df = pd.read_csv(f"data/{option_symbol}_{time_frame}.csv")
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
                
                print(f"✅ ENTRY: {option_symbol} ({time_frame}) at ${entry_price:.4f}")
            
            
    def check_for_exit(self, option_symbol):
        for time_frame in self.time_frames:
            # Read csv
            df = pd.read_csv(f"data/{option_symbol}_{time_frame}.csv")
            
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
                with open(f"data/{option_symbol}_{time_frame}_entry_exit.csv", "a") as f:
                    f.write(f"{option_symbol},{time_frame},{entry_price},{exit_price},{profit_loss}\n")

                pnl_status = "PROFIT" if profit_loss >= 0 else "LOSS"
                print(f"🔚 EXIT: {option_symbol} ({time_frame}) at ${exit_price:.4f} - {pnl_status}: ${profit_loss:.4f}")

        
    def process_data(self, option_symbols):
        """
        Process data (aggregate, calculate indicators, check entry/exit)
        """
        print(f"⚙️  Starting data processing at {datetime.now().strftime('%H:%M:%S')}")
        
        # Aggregate minute data to create 5min and 10min timeframes
        for symbol in option_symbols:
            self.aggregate_minute_data(symbol)

        # Calculate indicators for each timeframe
        for time_frame in self.time_frames:
            for symbol in option_symbols:
                self.calculate_indicators(symbol, time_frame)

        # Check for entry
        for symbol in option_symbols:
            self.check_for_entry(symbol)

        # Check for exit
        for symbol in option_symbols:
            self.check_for_exit(symbol)
            
        print(f"✅ Data processing completed at {datetime.now().strftime('%H:%M:%S')}")

    def generate_option_symbol_for_date(self, symbol, strike_price, option_type, base_date):
        """
        Generate an option symbol for a specific base date (for backtesting)
        """
        # Add 2 business days to base date
        expiry_date = base_date + timedelta(days=2)

        # Check if expiry is a weekend and adjust
        if expiry_date.weekday() == 5:  # Saturday
            expiry_date += timedelta(days=2)
        elif expiry_date.weekday() == 6:  # Sunday
            expiry_date += timedelta(days=1)

        # Format date as YYMMDD
        date_str = expiry_date.strftime('%y%m%d')
        
        # Format strike price as 8-digit string with 3 decimal places
        strike_str = f"{int(strike_price * 1000):08d}"
        
        # Validate option type
        option_type = option_type.upper()
        if option_type not in ['C', 'P']:
            raise ValueError("option_type must be 'C' for call or 'P' for put")
        
        # Combine all parts
        option_symbol = f"{symbol.upper()}{date_str}{option_type}{strike_str}"
        
        return option_symbol

    def show_results(self):
        """
        Display backtesting results
        """
        print("\n" + "="*50)
        print("📊 BACKTESTING RESULTS")
        print("="*50)
        
        if not self.trades:
            print("No trades were executed.")
            return
            
        total_pnl = sum(trade['profit_loss'] for trade in self.trades)
        winning_trades = [trade for trade in self.trades if trade['profit_loss'] > 0]
        losing_trades = [trade for trade in self.trades if trade['profit_loss'] <= 0]
        
        print(f"Total Trades: {len(self.trades)}")
        print(f"Winning Trades: {len(winning_trades)}")
        print(f"Losing Trades: {len(losing_trades)}")
        print(f"Win Rate: {(len(winning_trades)/len(self.trades)*100):.1f}%")
        print(f"Total P&L: ${total_pnl:.4f}")
        
        print("\nDetailed Trades:")
        for trade in self.trades:
            status = "WIN" if trade['profit_loss'] > 0 else "LOSS"
            print(f"  {trade['option_symbol']} ({trade['time_frame']}) - "
                  f"Entry: ${trade['entry_price']:.4f} → Exit: ${trade['exit_price']:.4f} "
                  f"= ${trade['profit_loss']:.4f} ({status})")

    def calculate_strike_date(self, start_date):
        """
        Calculate strike date: start_date + 2 days, with weekend adjustments
        - If Saturday: add 2 more days (to Monday)
        - If Sunday: add 2 more days (to Tuesday)
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        strike_dt = start_dt + timedelta(days=2)
        
        # Check if it lands on weekend and adjust
        if strike_dt.weekday() == 5:  # Saturday
            strike_dt += timedelta(days=2)  # Move to Monday
        elif strike_dt.weekday() == 6:  # Sunday
            strike_dt += timedelta(days=2)  # Move to Tuesday
            
        return strike_dt.strftime('%Y-%m-%d')

    def run(self, start_date=None, end_date=None):
        """
        Run backtesting for a specific date range
        """
        if start_date is None:
            start_input = input("Enter start date for data fetching (mm-dd-yyyy): ")
            try:
                month, day, year = start_input.split('-')
                start_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                print("❌ Invalid start date format. Please use mm-dd-yyyy")
                return
                
        if end_date is None:
            end_input = input("Enter end date for data fetching (mm-dd-yyyy): ")
            try:
                month, day, year = end_input.split('-')
                end_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except ValueError:
                print("❌ Invalid end date format. Please use mm-dd-yyyy")
                return

        # Calculate strike date automatically (start_date + 2 days with weekend adjustments)
        strike_date = self.calculate_strike_date(start_date)

        print(f"🔄 Starting backtesting from {start_date} to {end_date} (strikes from {strike_date})")
        
        # Get strike prices for the start date (no rounding)
        strike_price_1 = self.get_open_price("SPY", start_date)
        strike_price_2 = strike_price_1 - 1

        print(f"📊 SPY strike prices: ATM=${strike_price_1}, OTM=${strike_price_2}")

        # Generate option symbols (using strike date for expiry calculation)
        strike_dt = datetime.strptime(strike_date, '%Y-%m-%d')
        option_symbol_1_c = self.generate_option_symbol_for_date("SPY", round(strike_price_1), "C", strike_dt)
        option_symbol_1_p = self.generate_option_symbol_for_date("SPY", round(strike_price_1), "P", strike_dt)
        option_symbol_2_c = self.generate_option_symbol_for_date("SPY", round(strike_price_2), "C", strike_dt)
        option_symbol_2_p = self.generate_option_symbol_for_date("SPY", round(strike_price_2), "P", strike_dt)

        option_symbols = [option_symbol_1_c, option_symbol_1_p, option_symbol_2_c, option_symbol_2_p]
        print(f"📈 Option symbols: {', '.join(option_symbols)}")

        # Initialize entries structure
        self.initialize_entries(option_symbols)

        # Fetch data for all symbols using the date range
        print(f"📥 Fetching data from {start_date} to {end_date}")
        for symbol in option_symbols:
            self.fetch_ohlcv(symbol, start_date, end_date)
            
        # Process data
        print(f"⚙️  Processing data")
        self.process_data(option_symbols)
        print(f"✅ Backtesting completed")
        
        # Show results
        self.show_results()




if __name__ == "__main__":
    tracker = OptionsTracker()
    tracker.run()
