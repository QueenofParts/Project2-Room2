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

