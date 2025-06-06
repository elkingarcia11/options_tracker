# Options Backtesting Tool

A comprehensive options trading strategy backtesting tool that analyzes SPY options using technical indicators across multiple timeframes for historical data analysis.

## Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set up API key**: Create `.env` file with `POLYGON_API_KEY=your_key_here`
3. **Run backtesting**: `python options_tracker.py`
4. **Enter date ranges**: Input start date, end date for analysis
5. **Review results**: Check the detailed backtesting output and `data/` folder

## Overview

This backtesting tool analyzes 4 SPY option contracts for any historical date range:

- **ATM Call** (at SPY open price from start date)
- **ATM Put** (at SPY open price from start date)  
- **OTM Call** ($1 below SPY open price from start date)
- **OTM Put** ($1 below SPY open price from start date)

It processes historical price action across three timeframes (1min, 5min, 10min) and simulates trades based on technical indicator confluences.

## Key Features

### 📊 **Historical Backtesting**
- **Date range analysis**: Test strategies on any historical period
- **Precise data**: No rounding of prices or technical indicators
- **Multiple timeframes**: 1-minute, 5-minute, and 10-minute analysis
- **Comprehensive results**: Win rate, P&L, and detailed trade breakdown

### 🎯 **Smart Strike Selection**
- **Automatic calculation**: Strike date = start date + 2 business days
- **Weekend handling**: 
  - Saturday → Monday (+ 2 more days)
  - Sunday → Tuesday (+ 2 more days)
- **Real market prices**: Uses actual SPY open prices for strike determination

### 📁 **Organized Data Management**
- All historical data saved to `data/` folder
- Separate files for each timeframe and option symbol
- Trade records with entry/exit prices and P&L
- No data loss between runs

## Trading Strategy

### Entry Conditions (ALL must be true):
- **EMA(7) > VWMA(17)** - Trend momentum
- **ROC(8) > 0** - Rate of change positive  
- **MACD Line > MACD Signal** - MACD bullish crossover
- **No existing position** for that timeframe

### Exit Conditions (At least 2 out of 3 must be true):
- **EMA(7) < VWMA(17)** - Trend momentum reversal
- **ROC(8) < 0** - Rate of change negative
- **MACD Line < MACD Signal** - MACD bearish crossover

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
```
polygon-api-client
python-dotenv
pandas
pytz
```

### 2. Environment Variables

Create a `.env` file in the project root:

```
POLYGON_API_KEY=your_polygon_api_key_here
```

Get your API key from [Polygon.io](https://polygon.io/) (free tier works for historical data)

## Usage

### Running Backtests

```bash
python options_tracker.py
```

**Interactive prompts:**
1. **Start date** (mm-dd-yyyy): Beginning of analysis period
2. **End date** (mm-dd-yyyy): End of analysis period

**Automatic calculations:**
- **Strike prices**: Fetched from SPY open price on start date
- **Strike date**: Automatically calculated (start date + 2 business days with weekend adjustments)
- **Option symbols**: Generated using strike prices and strike date

### Example Session

```
Enter start date for data fetching (mm-dd-yyyy): 06-05-2024
Enter end date for data fetching (mm-dd-yyyy): 06-07-2024

🔄 Starting backtesting from 2024-06-05 to 2024-06-07 (strikes from 2024-06-09)
📊 SPY strike prices: ATM=$524.50, OTM=$523.50
📈 Option symbols: SPY240609C00524500, SPY240609P00524500, SPY240609C00523500, SPY240609P00523500
📥 Fetching data from 2024-06-05 to 2024-06-07
✅ Saved 1247 OHLCV records for SPY240609C00524500
⚙️ Processing data
📊 Aggregated 1247 1min → 416 5min → 208 10min candles
✅ ENTRY: SPY240609C00524500 (5min) at $2.1500
🔚 EXIT: SPY240609C00524500 (5min) at $2.8700 - PROFIT: $0.7200
✅ Backtesting completed

==================================================
📊 BACKTESTING RESULTS
==================================================
Total Trades: 3
Winning Trades: 2
Losing Trades: 1
Win Rate: 66.7%
Total P&L: $1.2400
```

### Date Logic Examples

| Start Date | Strike Date | Calculation | Adjustment |
|------------|-------------|-------------|------------|
| Mon 06-05 | Wed 06-07 | +2 days | None |
| Thu 06-06 | **Sat 06-08** | +2 days → **Mon 06-10** | +2 more (Saturday) |
| Fri 06-07 | **Sun 06-09** | +2 days → **Tue 06-11** | +2 more (Sunday) |

## Output Files

All files are organized in the `data/` folder:

### Price Data Files
- `data/{option_symbol}_1min.csv` - 1-minute OHLCV data
- `data/{option_symbol}_5min.csv` - 5-minute aggregated data  
- `data/{option_symbol}_10min.csv` - 10-minute aggregated data

### Trade Records
- `data/{option_symbol}_{timeframe}_entry_exit.csv` - Individual trade records with P&L

### File Formats

#### OHLCV Files
```csv
timestamp,open,high,low,close,volume
1717603800000,2.15,2.18,2.12,2.17,1250
```

#### Trade Files
```csv
option_symbol,timeframe,entry_price,exit_price,profit_loss
SPY240609C00524500,5min,2.1500,2.8700,0.7200
```

## Technical Indicators

- **EMA(7)**: 7-period Exponential Moving Average
- **VWMA(17)**: 17-period Volume Weighted Moving Average  
- **EMA(12/26)**: 12 and 26-period EMAs for MACD calculation
- **MACD**: Moving Average Convergence Divergence
- **MACD Signal**: 9-period EMA of MACD line
- **ROC(8)**: 8-period Rate of Change

*All calculations preserve full precision with no rounding*

## Data Precision

### No Rounding Policy
- **Strike prices**: Exact SPY open prices (e.g., $524.47, not $524)
- **Technical indicators**: Full precision calculations
- **Entry/exit prices**: Exact option prices from market data
- **P&L calculations**: Precise to 4 decimal places

### Aggregation Logic
- **5-minute candles**: Resampled from all available 1-minute data
- **10-minute candles**: Resampled from all available 1-minute data
- **Missing periods**: Automatically handled and excluded
- **Timezone**: All timestamps in milliseconds (UTC)

## Historical Analysis

### Supported Date Ranges
- **Minimum**: Any date with available Polygon data
- **Maximum**: Any historical date (free tier = previous day)
- **Granularity**: 1-minute resolution for precise analysis
- **Market hours**: Standard trading hours data only

### Strategy Performance Metrics
- **Total trades**: Count of completed entry/exit cycles
- **Win rate**: Percentage of profitable trades
- **Total P&L**: Sum of all trade profits/losses
- **Individual trades**: Detailed entry/exit analysis per timeframe

## Project Structure

```
options_tracker/
├── options_tracker.py          # Main backtesting engine
├── requirements.txt             # Python dependencies
├── .env                        # API key configuration
├── README.md                   # This documentation
└── data/                       # Generated data files
    ├── SPY240609C00524500_1min.csv
    ├── SPY240609C00524500_5min.csv
    ├── SPY240609C00524500_10min.csv
    └── SPY240609C00524500_1min_entry_exit.csv
```

## Troubleshooting

### Common Issues

1. **API Authentication Error**
   - Check `.env` file exists with correct API key
   - Verify Polygon.io account is active
   - Ensure API key has historical data access

2. **No data for date range**
   - Verify dates are historical (not future)
   - Check dates fall on trading days
   - Ensure option symbols existed during that period

3. **Missing timeframe data**
   - Insufficient 1-minute data for aggregation
   - Check if market was open during specified period
   - Verify date format (YYYY-MM-DD)

4. **File permission errors**
   - Ensure write access to `data/` directory
   - Check disk space availability
   - Verify no files are open in other applications

### Data Validation

```bash
# Check generated files
ls -la data/

# View recent trades
tail data/*_entry_exit.csv

# Verify data completeness
wc -l data/*_1min.csv
```

## Development

### Testing Backtests

```bash
# Quick test with recent data
python options_tracker.py
# Enter: 05-01-2024 to 05-03-2024

# Extended analysis
python options_tracker.py  
# Enter: 01-01-2024 to 03-31-2024
```

### Customization Options

- **Strike offsets**: Modify `strike_price_2 = strike_price_1 - 1` in run()
- **Technical periods**: Adjust EMA/VWMA periods in calculate_indicators()
- **Entry/exit rules**: Modify conditions in check_for_entry()/check_for_exit()
- **Timeframes**: Add/remove from self.time_frames in __init__()
- **Date logic**: Modify calculate_strike_date() for different expiry rules

### Performance Considerations

- **Memory usage**: Large date ranges require more RAM
- **API limits**: Free tier has request limits
- **Processing time**: 1-minute data is computation-intensive
- **Storage**: Each symbol generates ~3 CSV files

## API Limitations

### Polygon.io Free Tier
- **Historical data**: Previous day and earlier
- **Rate limits**: 5 requests per minute
- **Data delay**: End-of-day data only
- **Upgrade**: Required for real-time or current day data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with various date ranges
4. Submit a pull request

## License

This project is for educational and research purposes. Historical backtesting results do not guarantee future performance. Use at your own risk for actual trading decisions.
