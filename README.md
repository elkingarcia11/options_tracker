# Options Tracker

A real-time options trading strategy tracker that monitors SPY options using technical indicators and executes trades based on predefined signals across multiple timeframes.

## Overview

This tracker monitors 4 SPY option contracts:

- ATM Call (at current SPY price)
- ATM Put (at current SPY price)
- OTM Call ($1 below current SPY price)
- OTM Put ($1 below current SPY price)

It analyzes price action across three timeframes (1min, 5min, 10min) and executes trades based on technical indicator confluences.

## Trading Strategy

### Entry Conditions (ALL must be true):

- EMA(7) > VWMA(17)
- ROC(8) > 0
- MACD Line > MACD Signal
- No existing open position for that timeframe

### Exit Conditions (At least 2 out of 3 must be true):

- EMA(7) < VWMA(17)
- ROC(8) < 0
- MACD Line < MACD Signal

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```
POLYGON_API_KEY=your_polygon_api_key_here
```

Get your free API key from [Polygon.io](https://polygon.io/)

### 3. Update Requirements

Make sure your `requirements.txt` contains:

```
polygon-api-client
python-dotenv
pandas
```

## Usage

### Manual Run

```bash
python main.py
```

### Cron Job Setup (Recommended)

#### Option 1: Run every minute during market hours

```bash
# Edit crontab
crontab -e

# Add this line to run Monday-Friday, 9:30 AM - 4:00 PM EST
* 9-16 * * 1-5 cd /path/to/options_tracker && /usr/bin/python3 main.py
```

#### Option 2: Run every 5 minutes during market hours

```bash
# Run every 5 minutes during market hours
*/5 9-16 * * 1-5 cd /path/to/options_tracker && /usr/bin/python3 main.py
```

#### Option 3: Run at specific times

```bash
# Run at market open, mid-day, and close
30 9,12,16 * * 1-5 cd /path/to/options_tracker && /usr/bin/python3 main.py
```

## Output Files

The tracker generates several CSV files:

### Price Data Files

- `{option_symbol}_1min.csv` - 1-minute OHLCV data
- `{option_symbol}_5min.csv` - 5-minute aggregated data
- `{option_symbol}_10min.csv` - 10-minute aggregated data

### Trade Files

- `{option_symbol}_{timeframe}_entry_exit.csv` - Individual trade records

### File Formats

#### OHLCV Files

```csv
timestamp,open,high,low,close,volume
```

#### Trade Files

```csv
option_symbol,timeframe,entry_price,exit_price,profit_loss
```

## Example Option Symbols

The tracker generates option symbols in standard format:

- `SPY241220C00580000` (SPY Call, Dec 20 2024, $580 strike)
- `SPY241220P00579000` (SPY Put, Dec 20 2024, $579 strike)

## Monitoring and Logs

### Check Cron Job Status

```bash
# View cron job logs
grep CRON /var/log/syslog

# Check if your job is scheduled
crontab -l
```

### Monitor Output Files

```bash
# Watch for new trades
tail -f *_entry_exit.csv

# Check latest price data
tail -f *_1min.csv
```

## Technical Indicators

- **EMA(7)**: 7-period Exponential Moving Average
- **VWMA(17)**: 17-period Volume Weighted Moving Average (using close price)
- **EMA(12/26)**: 12 and 26-period EMAs for MACD calculation
- **MACD**: Moving Average Convergence Divergence
- **MACD Signal**: 9-period EMA of MACD line
- **ROC(8)**: 8-period Rate of Change

## Important Notes

### Market Hours

- Options trade Monday-Friday, 9:30 AM - 4:00 PM EST
- Schedule cron jobs accordingly to avoid unnecessary API calls

### API Rate Limits

- Polygon.io has rate limits on free accounts
- Consider the frequency of your cron jobs to stay within limits

### Risk Management

- This is a tracking/backtesting tool - not live trading
- Always validate signals before actual trading
- Consider transaction costs, slippage, and market impact

### File Management

- CSV files will grow over time - consider log rotation
- Monitor disk space usage
- Archive old trade data periodically

## Troubleshooting

### Common Issues

1. **No data in CSV files**

   - Check API key in `.env` file
   - Verify internet connection
   - Check Polygon.io service status

2. **Cron job not running**

   - Check cron service: `sudo service cron status`
   - Verify file paths in crontab
   - Check cron logs for errors

3. **Permission errors**

   - Ensure Python script has execute permissions: `chmod +x main.py`
   - Check file/directory ownership

4. **Missing dependencies**
   - Reinstall requirements: `pip install -r requirements.txt`
   - Check Python path in cron job

## Development

### Testing

```bash
# Test with a single run
python main.py

# Check generated files
ls -la *.csv
```

### Customization

- Modify strike price offsets in `run()` method
- Adjust technical indicator periods in `calculate_indicators()`
- Change timeframes in `__init__()` method
- Add new entry/exit conditions in respective methods

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and research purposes. Use at your own risk for actual trading.
