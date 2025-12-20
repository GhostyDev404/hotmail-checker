## Features

- ✅ Proxy support
- ✅ Real-time statistics with CPM tracking
- ✅ Automatic result categorization (Hits, 2FA, Custom, Bad)
- ✅ Color-coded console output
- ✅ Auto-saves results to separate files
- ✅ No data loss - ensures all hits are saved

## Installation

1. Make sure Python is installed
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the checker:
   ```
   python main.py
   ```

## Setup

1. Add your combos to `combos.txt` in the format: `email:password` (one per line)
2. Run the checker

## Usage

1. Run `python main.py`
2. Enter number of threads
3. Choose if you want to use proxies
4. If using proxies, enter proxy in format: `http://ip:port` or `http://user:pass@ip:port`
5. Wait for checking to complete
6. Results will be saved in the `results` folder

## Results

Results are automatically saved to the `results` folder with timestamps:

- `hits_YYYYMMDD_HHMMSS.txt` - Valid accounts
- `2fa_YYYYMMDD_HHMMSS.txt` - Accounts with 2FA enabled
- `custom_YYYYMMDD_HHMMSS.txt` - Custom status accounts

## Statistics

During checking, you'll see real-time stats:
- **Progress** - Current position / Total combos
- **Hits** - Valid accounts found
- **2FA** - Accounts with two-factor authentication
- **Custom** - Custom status accounts
- **Bad** - Invalid accounts
- **CPM** - Checks Per Minute

## Final Report

After completion, you'll see:
- Time elapsed
- CPM (Checks Per Minute)
- Total checked
- Breakdown of all results

## Requirements

- Python 3.7+
- Windows/Linux/MacOS
- (Optional) Proxy for anonymous checking

**Module not found error:**
- Run `pip install -r requirements.txt`
- Make sure Python and pip are properly installed

## Notes

- All results are saved with timestamps
- Multiple runs won't overwrite previous results
- The checker handles errors automatically and continues
- Press Ctrl+C to stop checking at any time

**Version:** 1.0  
**Last Updated:** December 2025