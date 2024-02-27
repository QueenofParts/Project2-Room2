"""
This file houses all functions used within this project.
"""

def get_html_results():

    """
    The exported files used to analyze are in html format.  This function uses
    os.listdir() to pull in a list of files within resources/html folder. It
    then loops through the list of files, reading in each one with minor formatting
    then concats it to a DataFrame holder to return.
    """
    import pandas as pd
    import os
    
    # Create list of html files in the html folder: Does not weed out non-html
    html_pages = os.listdir("resources/html")

    # Create DataFrame to concat to
    compiled_df = pd.DataFrame()

    # Loop through html_pages list to pull in
    for page in html_pages:

        # Read in the file using pandas
        # Render the 3rd row as data header skipping the first two rows
        df = pd.read_html(f"resources/html/{page}", header=2)

        # Pull the first Table which is the only table in the html page
        data_df = pd.DataFrame(df[0])

        # Convert Ticket to numeric and coerce the rest to NaN
        data_df['Ticket'] = pd.to_numeric(data_df['Ticket'], errors="coerce")

        # Keep only that of Ticket and Size that is not null
        # This keeps trade data then removes the first row of balance
        data_df = data_df[(pd.notnull(data_df['Ticket'])) & (pd.notnull(data_df['Size']))]
        compiled_df = pd.concat([compiled_df, data_df], axis="rows")

        return compiled_df

def get_daily_series(symbol, API_KEY):

    """
    This function calls 5 minute interval time series data from a stock of choice.
    A symbol and an API_KEY is required.  It can be a free version but remember
    the limitations of calls per day.  After it gathers and formats the data,
    the data is grouped into daily totals as a daily_stock_df DataFrame.  Both
    are saved to an excel file of the symbol name with Daily information placed
    into 'daily' worksheet and '5 min interval' into 'interval' worksheet
    """
    # Import needed modules
    import requests
    import pandas as pd

    # Pull the information
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&outputsize=full&apikey={API_KEY}'
    data = requests.get(url).json()

    # Format and make into DataFrame
    data_df = pd.DataFrame(data['Time Series (5min)']).T
    stock_df = data_df.apply(pd.to_numeric, errors='ignore')
    stock_df = stock_df.rename(columns={'1. open':'Open', '2. high':'High', 
                        '3. low': 'Low','4. close':'Close','5. volume':'Volume'})
    stock_df.index = pd.to_datetime(stock_df.index)

    # Create daily information
    daily_stock_df = stock_df.groupby(pd.Grouper(freq='D')).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })

    try:
        # Save the information to an excel file in separate sheets
        # MUST pip install xlsxwriter if not already installed
        writer = pd.ExcelWriter(f'resources/stocks_etfs/{symbol}.xlsx', engine='xlsxwriter')
        stock_df.to_excel(writer, sheet_name='Interval', index=True, header=True)
        daily_stock_df.to_excel(writer, sheet_name='Daily', index=True, header=True)
        writer.close()
    except:
        print(f"Could not save {symbol}.")

    # Return DataFrame
    return stock_df, daily_stock_df

def get_stock_etf_listings(budget):
    
    import pandas as pd

    # Import file of stock listings
    df = pd.read_excel("resources/listing_info.xlsx")
    df = df.fillna(0)

    # Make columns float
    df = df.astype({"volume.std":float, 
                    "volume":float,
                    "last open":float,
                    "last close": float,
                    "H/L Delta": float,
                    "trending %": float})

    # Keep only those under budget only Stock removing ETF
    df = df.loc[(df['last close'] <= budget) & (df['assetType'] == "Stock")]
    return df

def get_market_listings(API_KEY):
    
    # Import needed modules
    import requests
    import pandas as pd
    import csv
    
    # Pull the information
    CSV_URL = f'https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={API_KEY}'

    with requests.Session() as s:
        download = s.get(CSV_URL)
        decoded_content = download.content.decode('utf-8')
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        my_list = list(cr)

    # Format and make into DataFrame
    df = pd.DataFrame(my_list[1:], columns=my_list[0])
    
    # Add columns for calculations
    add_col = ['volume.std', 
               'volume', 
               'last open',
               'last close',
               'H/L Delta',
               'trending %']
    df[add_col] = ''

    # Return DataFrame
    return df