import pandas as pd
from dotenv import load_dotenv
import os, time, requests, csv
from datetime import datetime
import numpy as np
from prophet import Prophet

def get_market_listings(API_KEY):
    
    # Pull the information
    CSV_URL = f'https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={API_KEY}'

    with requests.Session() as s:
        download = s.get(CSV_URL)
        decoded_content = download.content.decode('utf-8')
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        my_list = list(cr)

    # Format and make into DataFrame
    # my_list[1:] calls all from list except first item since it is a header
    # columns = my_list[0] designates column headers being the first item
    df = pd.DataFrame(my_list[1:], columns=my_list[0])
    
    # Add columns for calculations
    add_col = ['volume.std', 'volume', 'last open', 'last close', 'H/L Delta',
               'trending %']
    df[add_col] = 0

    writer = pd.ExcelWriter('resources/listing_info.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name="Stock Listings", index=False, header=True)
    writer.close()

    # Return DataFrame
    return df

def get_listings():

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
    df = df.loc[df['status'] == "Active"]

    return df

def get_company_overview(symbol_list, API_KEY):
    # Set up DataFrame
    company_info = pd.DataFrame()
    for i, symbol in enumerate(symbol_list, start=0):
        try:
            overview_url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
            overview = requests.get(overview_url).json()
            overview = pd.DataFrame(overview, index=[0])
            company_info = pd.concat([company_info, overview], axis="rows")
        except:
            #print(f"Error with {symbol}")
            # Append error message
            process_message = f'(get_company_overview) Error with symbol {symbol}: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f = open("errors.txt", "a")
            f.write(process_message)
            f.close()

        # Take an API break 30 API calls per minute
        if i % 29 == 0 and i != 0:
            time.sleep(61)
    
    company_info = company_info.reset_index(drop=True)
    writer = pd.ExcelWriter('resources/company_overveiw.xlsx', engine='xlsxwriter')
    company_info.to_excel(writer, sheet_name="Company Overview", index=False, header=True)
    writer.close()

    return company_info

def get_daily_series(symbol_list, API_KEY):

    # Start the loop for list of symbols
    for i, symbol in enumerate(symbol_list, start=0):
        try:
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

            stock_df = stock_df.sort_index(ascending=True)
            stock_df['price_diff'] = stock_df['Close'].diff()
            stock_df['volatility'] = 0
            stock_df = stock_df.reset_index(drop=False)
            for s, row in enumerate(stock_df['Close'], start=0):
                stock_df.loc[s,'volatility'] = np.std(stock_df.iloc[:s]['Close'].pct_change()) * np.sqrt(s)
            
            stock_df['volatility_diff'] = stock_df['volatility'].diff()

            # Make datetime index again
            stock_df = stock_df.set_index('index')

            # Save the information to an excel file in separate sheets
            # MUST pip install xlsxwriter if not already installed
            writer = pd.ExcelWriter(f'resources/stocks_etfs/{symbol}.xlsx', engine='xlsxwriter')
            stock_df.to_excel(writer, sheet_name='Interval', index=True, header=True)
            daily_stock_df.to_excel(writer, sheet_name='Daily', index=True, header=True)
            writer.close()

        except:
            # print(f"Could not save {symbol}.")
            # Append error message
            process_message = f'(get_daily_series) Error with symbol {symbol}: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f = open("errors.txt", "a")
            f.write(process_message)
            f.close()
        
        # Take an API break 30 API calls per minute
        if i % 29 == 0 and i != 0:
            time.sleep(61)

    # Return DataFrame
    return stock_df, daily_stock_df

def prediction_series(df, p_col, periods):
    """
    This function uses the Prophet model to predict future data.  It resamples
    the data given for a continuous datetime index at 5 minute intervals from
    date min to date max.  The resampling reindexes the dataframe for the rest
    of the process.
    df = DataFrame
    p_col = Primary Column to use for y
    periods = periods for make_future_dataframe
    """
    # Resample
    start = df.index.min().floor('D')
    end = df.index.max().ceil('D')
    new_index = pd.date_range(start=start, end=end, freq='5T')
    df = df.reindex(new_index)
    df = df.fillna(0)
    
    # Prepare columns for Prophet
    df = df.reset_index()[['index', p_col]]
    df = df.rename(columns={"index":"ds", p_col:"y"})
    df = df.dropna()

    # Use Prophet to make future dataframe
    m=Prophet()
    m.fit(df)
    future = m.make_future_dataframe(periods=periods, freq="5T")
    forecast = m.predict(future)

    # Create forecast range using the periods times -1.
    forecast_range = forecast[['ds','yhat', 'yhat_lower', 'yhat_upper']].iloc[(periods*-1):,:]

    return forecast, forecast_range