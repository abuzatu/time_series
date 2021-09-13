import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, AutoMinorLocator
import datetime
import yfinance as yf
import hvplot.pandas
import logging
from pathlib import Path, PurePath

LOCALIZE_US_STOCK_MARKET = "America/New_York"

# logging level: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_list_stock_ticker_in_folder(input_folder_name: str) -> list:
    '''get list of all the tickers available'''
    p = Path(input_folder_name).rglob("df_*.pickle")
    list_stock_ticker = sorted(set([x.name.split(".")[0].split("_")[-1] for x in p if x.is_file()]))
    logging.debug("list_stock_sticker from folder:")
    for stock_ticker in list_stock_ticker:
        logging.debug(stock_ticker)
    return list_stock_ticker

def get_list_stock_ticker_from_file(input_file_name: str) -> list:
    list_stock_ticker = []
    try:
        f = open(input_file_name)
        lines = f.readlines()
        for line in lines:
            line = line.rstrip()
            if line.startswith("#"):
                continue
            list_stock_ticker.append(line)
    except IOError:
        raise RuntimeError (f"File {input_file_name} not accessible.")
    finally:
        f.close()
    logging.debug("list_stock_sticker from file:")
    for stock_ticker in list_stock_ticker:
        logging.debug(stock_ticker)
    return list_stock_ticker

def concat_df_for_different_dates(
    output_folder_name: str,
    stock_ticker: str = "ZOM",
    date_start: str = "1995-01-20",
    suffix: str = "al",
) -> pd.DataFrame:
    '''Example of code to concatenate data frames for a ticker for different dates with different granularities.'''
    df1 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_{date_start}_2019-01-11_1d_{stock_ticker}.pickle")
    df2 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2019-01-11_2020-11-11_1h_{stock_ticker}.pickle")
    df3 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2020-11-11_2020-12-11_5m_{stock_ticker}.pickle") # 2m
    df4 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2020-12-11_2020-12-18_1m_{stock_ticker}.pickle")
    df5 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2020-12-18_2020-12-25_1m_{stock_ticker}.pickle")
    df6 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2020-12-25_2021-01-01_1m_{stock_ticker}.pickle")
    df7 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2021-01-01_2021-01-08_1m_{stock_ticker}.pickle")
    df8 = pd.read_pickle(f"{OUTPUT_FOLDER_NAME}/df_2021-01-08_2021-01-09_1m_{stock_ticker}.pickle")

    df = pd.concat([df1, df2, df3, df4, df5, df6, df7, df8], axis = 0)
    df.to_pickle(f"{OUTPUT_FOLDER_NAME}/df_{date_start}_2021-01-09_{suffix}_{stock_ticker}.pickle")

    df = df[df.index > pd.to_datetime("2019-01-01").tz_localize(LOCALIZE_US_STOCK_MARKET )]
    df.to_pickle(f"{OUTPUT_FOLDER_NAME}/df_2019-01-01_2021-01-09_{suffix}_{stock_ticker}.pickle")
    
    return df

def get_subset_df(
    df: pd.DataFrame,
    start: str,
    end: str = None,
) -> pd.DataFrame:
    series = df.index >= pd.to_datetime(start).tz_localize(LOCALIZE_US_STOCK_MARKET)
    if end is not None:
        series = series & (df.index <= pd.to_datetime(end).tz_localize(LOCALIZE_US_STOCK_MARKET))
    return df[series]

def update_df_1d(
    df: pd.DataFrame,
    datetime: pd.Timestamp
) -> None:
    # this is for one day interval
    dt = df[datetime]
    date = None
    list_datetime_start = []
    list_datetime_end = []
    for i in range(len(df)):
        datetime_start = dt[i].tz_localize(LOCALIZE_US_STOCK_MARKET) + pd.Timedelta(9.5, unit = "h")
        datetime_end = datetime_start + pd.Timedelta(6.5, unit = "h") # there are 6.5 trading hours
        # logging.debug(f"i={i}, datetime_start={datetime_start}, datetime_end={datetime_end}")
        list_datetime_start.append(datetime_start)
        list_datetime_end.append(datetime_end)
    df["datetime_start"] = list_datetime_start
    df["datetime_end"] = list_datetime_end

def update_df_1h(df, datetime, interval_number, interval_unit, interval_number_short):
    # this is for one hour interval
    dt = df[datetime]
    date = None
    list_datetime_start = []
    list_datetime_end = []
    for i in range(len(df)):
        dti = dt[i].tz_localize(LOCALIZE_US_STOCK_MARKET)
        dti = dti + pd.Timedelta(8.5, unit = "h")
        if dti != date:
            date = dti
            counter = 0
            datetime_start = date
            new_date = False
        # increase another hour
        counter += 1
        interval = interval_number
        if counter == 7:
            interval = interval_number_short
        datetime_start = datetime_start + pd.Timedelta(interval_number, unit = interval_unit)
        datetime_end = datetime_start + pd.Timedelta(interval, unit = interval_unit)
        # logging.debug(f"i={i}, counter={counter}, datetime_start={datetime_start}, datetime_end={datetime_end}")
        list_datetime_start.append(datetime_start)
        list_datetime_end.append(datetime_end)
    df["datetime_start"] = list_datetime_start
    df["datetime_end"] = list_datetime_end

def update_df_min(df, datetime, interval_number, interval_unit):
    # this is for N minutes interval
    dt = df[datetime]
    date = None
    list_datetime_start = []
    list_datetime_end = []
    for i in range(len(df)):
        datetime_start = dt[i]
        datetime_end = datetime_start + pd.Timedelta(interval_number, unit = interval_unit) 
        # logging.debug(f"i={i}, datetime_start={datetime_start}, datetime_end={datetime_end}")
        list_datetime_start.append(datetime_start)
        list_datetime_end.append(datetime_end)
    df["datetime_start"] = list_datetime_start
    df["datetime_end"] = list_datetime_end
    
def read_data(stock_ticker,
              period,
              date_start,
              date_end,
              interval,
              add_outside_trading_hours,
              add_dividends_and_stock_splits,
              auto_adjust):
    
    logging.debug(f'''Start read_data with
    stock_ticker = {stock_ticker},
    period = {period},
    date_start = {date_start},
    date_end = {date_end},
    add_dividends_and_stock_splits={add_dividends_and_stock_splits},
    auto_adjust={auto_adjust}''')
    
    # fix a bug in yfinance of not applying the localization when this option is on
    # my guess it is it ignores the tz already set on this date, it sets to maybe UTC
    # then it convers to US and thus shows from the previous day as well
    # so we add it back what will be subtracted by the time difference between us and New York
    if add_outside_trading_hours:
        if date_start is not None:
            date_start += pd.Timedelta (6, "h")
        if date_end is not None:
            date_end += pd.Timedelta (6, "h")
    
    # 
    if interval == "1d" or interval == "1h":
        datetime = "Date"
        if interval == "1h":
            interval_number_short = 0.5
    elif interval == "30m" or interval == "15m" or interval == "5m" or interval == "2m" or interval == "1m":
        datetime = "Datetime"
    else:
        raise RuntimeError(f"interval={interval} is not well defined!")
    
    #
    interval_number = int(interval[0:-1])
    interval_unit = interval[-1:]

    # create the ticker for the desired company
    logging.debug(f"Create ticker for {stock_ticker}.")
    ticker = yf.Ticker(stock_ticker)
    
    # read the historical data into a data frame
    logging.debug(f'''Start ticker.history()''')
    df_original = ticker.history(
        period = period,
        start = date_start,
        end = date_end,
        interval = interval,
        prepost = add_outside_trading_hours,
        actions = add_dividends_and_stock_splits,
        auto_adjust = auto_adjust,
        )
    
    if len(df_original) == 0:
        logging.warning(f"df_original has {len(df_original)} entries for {stock_ticker} between {date_start} to {date_end}.")
        return df_original

    # For the 1h interval, there is a bug as it returns a date without the time, so we need to add by hand
    # There are 7 intervals for every day, sometimes fewer if there is a short day
    # The stock market usually starts at 9:30 am and ends at 5 pm.
    # so the last interval has only 30 minutes.
    logging.debug(f"Introduce datetime_start and datetime_end for {stock_ticker}.")
    df = df_original.reset_index()
    if interval == "1d":
        update_df_1d(df, datetime)
    elif interval == "1h":
        update_df_1h(df, datetime, interval_number, interval_unit, interval_number_short)
    elif interval.endswith("m"):
        update_df_min(df, datetime, interval_number, interval_unit)
    else:
        raise RuntimeError(f"interval={interval} not known!")

    # 
    # 
    logging.debug(f"Reorganize columns for {stock_ticker}.")
    list_column = ["datetime_start", "datetime_end", "Open", "High", "Low", "Close", "Volume"]
    df = df[list_column]
    
    # set index to one datetime
    my_datetime = "datetime_end"
    df.set_index(my_datetime, inplace = True)
    df = df.sort_index()
    
    return df

def get_list_date(str_date_start, str_date_end):
    date_today = pd.Timestamp.today().normalize()
    date_start_1h = date_today - pd.Timedelta(730 - 1, "d")
    date_start_2m = date_today - pd.Timedelta(60 - 1, "d")
    date_start_1m = date_today - pd.Timedelta(30 - 1 , "d")
    
    date_start_1d = pd.to_datetime(str_date_start)
    
    if str_date_end == "today":
        date_end = date_today
    else:    
        date_end = pd.to_datetime(str_date_end)
    
    list_date = []
    if date_end <= date_start_1d:
        raise RuntimeError(f"date_end={date_end} <= date_start_1d={date_start_1d}")
    elif date_end <= date_start_1h:
        list_date.append((date_start_1d, date_end, "1d"))
    elif date_end <= date_start_2m:
        list_date.append((date_start_1d, date_start_1h, "1d"))
        list_date.append((date_start_1h, date_end, "1h"))
    elif date_end <= date_start_1m:
        list_date.append((date_start_1d, date_start_1h, "1d"))
        list_date.append((date_start_1h, date_start_2m, "1h"))
        list_date.append((date_start_2m, date_end, "2m"))
    elif date_end <= date_today:
        list_date.append((date_start_1d, date_start_1h, "1d"))
        list_date.append((date_start_1h, date_start_2m, "1h"))
        list_date.append((date_start_2m, date_start_1m, "2m"))
        # now comes an extra constraint that in this last 30 days interval
        # we can query for 1 minute interval in just 7 days long intervals
        # so we need to query several times (maximum 4 times)
        # first let's evaluate the boundaries for these
        date_start_1m_0 = date_start_1m + pd.Timedelta(0 * 7, "d")
        date_start_1m_1 = date_start_1m + pd.Timedelta(1 * 7, "d")
        date_start_1m_2 = date_start_1m + pd.Timedelta(2 * 7, "d")
        date_start_1m_3 = date_start_1m + pd.Timedelta(3 * 7, "d")
        date_start_1m_4 = date_start_1m + pd.Timedelta(4 * 7, "d")
        logging.debug(f"date_start_1m_0={date_start_1m_0}")
        logging.debug(f"date_start_1m_1={date_start_1m_1}")
        logging.debug(f"date_start_1m_2={date_start_1m_2}")
        logging.debug(f"date_start_1m_3={date_start_1m_3}")
        logging.debug(f"date_start_1m_4={date_start_1m_4}")
        if date_end <= date_start_1m_1:
            list_date.append((date_start_1m_0, date_end, "1m"))
        elif date_end <= date_start_1m_2:
            list_date.append((date_start_1m_0, date_start_1m_1, "1m"))
            list_date.append((date_start_1m_1, date_end, "1m"))
        elif date_end <= date_start_1m_3:
            list_date.append((date_start_1m_0, date_start_1m_1, "1m"))
            list_date.append((date_start_1m_1, date_start_1m_2, "1m"))
            list_date.append((date_start_1m_2, date_end, "1m"))
        elif date_end <= date_start_1m_4:
            list_date.append((date_start_1m_0, date_start_1m_1, "1m"))
            list_date.append((date_start_1m_1, date_start_1m_2, "1m"))
            list_date.append((date_start_1m_2, date_start_1m_3, "1m"))
            list_date.append((date_start_1m_3, date_end, "1m"))
        else:
            list_date.append((date_start_1m_0, date_start_1m_1, "1m"))
            list_date.append((date_start_1m_1, date_start_1m_2, "1m"))
            list_date.append((date_start_1m_2, date_start_1m_3, "1m"))
            list_date.append((date_start_1m_3, date_start_1m_4, "1m"))
            list_date.append((date_start_1m_4, date_end, "1m"))        
    else:
        raise RuntimeError(f"date_end={date_end} > date_today={date_today}")
    logging.info(f"list_date:")
    for date in list_date:
        logging.info(date)
    return list_date

def get_output_file_name(output_folder_name, date_start, date_end, interval, stock_ticker):
    return f"{output_folder_name}/df_{date_start}_{date_end}_{interval}_{stock_ticker}.pickle"

def get_df_from_list_date(
    stock_ticker: str,
    list_date: list,
    output_folder_name: str,
    period: str,
    add_outside_trading_hours: bool,
    add_dividends_and_stock_splits: bool,
    auto_adjust: bool,
    do_store_all_period_to_file: bool,
    do_store_only_some_period_to_file: bool,
    ):
    list_df = []
    for s, e, interval in list_date:
        date_start = s.tz_localize(LOCALIZE_US_STOCK_MARKET)
        date_end = e.tz_localize(LOCALIZE_US_STOCK_MARKET)
        logger.info(f"{stock_ticker} from {date_start} to {date_end} with interval {interval}")

        # read the data
        df = read_data(stock_ticker,
                   period,
                   date_start,
                   date_end,
                   interval,
                   add_outside_trading_hours,
                   add_dividends_and_stock_splits,
                   auto_adjust)
        
        #
        logger.info(f"len = {len(df)}")
        if len(df) > 0:
            #if stock_ticker == "AMRH":
            #    if interval.endswith("h") or interval.endswith("m"):
            #        # ajust by the stock split of 4 stocks -> 1 stock
            #        apply_split(df, 4, 1)
            # add to list
            list_df.append(df)
            # save for future
            ss = str(s.date())
            se = str(e.date())
            output_file_name = get_output_file_name(output_folder_name, ss, se, interval, stock_ticker)
            df.to_pickle(output_file_name )
            
    logging.debug(f"list_df has {len(list_df)} elements that we will concatenate.")
    # concatenate all to data framews
    df_all = pd.concat(list_df, axis = 0)
    logging.debug(f"df_all after concatenation has {len(df_all)} elements.\nfrom date {df_all.index[0]} to date {df_all.index[-1]}.")
    
    if do_store_all_period_to_file:
        logging.debug("Store the entire period of the stock existence to file.")
        date_all_start = str(list_date[0][0].date())
        date_all_end = str(list_date[-1][1].date())
        output_file_name = get_output_file_name(output_folder_name, date_all_start, date_all_end, "al", stock_ticker)
        df_all.to_pickle(output_file_name)
    
    if do_store_only_some_period_to_file:
        loging.debug("Store also only from a particular date onwards.")
        date_all_start = "2019-01-01"
        df_all_2 = df_all[df_all.index > pd.to_datetime(date_all_start).tz_localize(LOCALIZE_US_STOCK_MARKET)]
        output_file_name = get_output_file_name(output_folder_name, date_all_start, date_all_end, "al", stock_ticker)
        df_all_2.to_pickle(output_file_name)
    
    logging.debug("End get_df_from_list_date(). Return df_all")                  
    return df_all

def get_first_day_of_stock_ticker(
    input_file_name_info: str,
    stock_ticker: str,
    add_outside_trading_hours: bool = True,
    add_dividends_and_stocks_splits: bool = True,
    auto_adjust: bool = True,
) -> str:
    '''
    Return the first day when the stock started trading.
    Check if it is already stored in our pickle file.
    If not, query the database to collect it, then add to the pickle file.
    '''
    logging.info(f'Start get_first_day_of_stock_ticker({"stock_ticker"}).')
    # check if the file exists
    path = Path(input_file_name_info)
    if path.exists() == False:
        if True:
            raise RuntimeError(f"file {input_file_name_info} does not exist!")
        else:
            # maybe we want to create it
            df_info = pd.DataFrame([], columns = ["stock_ticker", "date_first"])
            df_info.set_index("stock_ticker", inplace = True)
            df_info.to_pickle(input_file_name_info)
    
    # if we are here, then the info pickle file exists, so let's open it
    df_info = pd.read_pickle(input_file_name_info)
    
    # check if the ticker is in the file and if so, return the data there
    if stock_ticker in df_info.index:
        logging.info("Start retrieve date_first from df_info.")
        str_date_start = df_info.loc[stock_ticker]["date_first"]
    else:
        # the ticker does not exist in the data frame, so we query the database to retrieve it.
        logging.info(f"Start query to find first date of stock_ticker={stock_ticker}.")
        df = read_data(stock_ticker,
                   "max",
                   None,
                   None,
                   "1d",
                   add_outside_trading_hours,
                   add_dividends_and_stocks_splits,
                   auto_adjust)
        # calculate list_date
        str_date_start = str(df.index[0].date())
        # update the data info data frame
        df_info.loc[stock_ticker] = str_date_start
        # sort to be again in alphabetical order
        df_info.sort_index(inplace = True)
        # save back to the same file
        df_info.to_pickle(input_file_name_info)
        
    # ready to return
    logging.info(f"First date of stock_ticker={stock_ticker} is {str_date_start}.")
    return str_date_start
    
def run_all_stock_stickers(
    input_folder_name_info: str,
    input_folder_name: str,
    input_file_name: str,
    output_folder_name: str,
    period: str,
    add_outside_trading_hours: bool,
    add_dividends_and_stocks_splits: bool,
    auto_adjust: bool,
):
    # data frame with ticker info
    input_file_name_info = input_file_name_info = f"{input_folder_name_info}/info.pickle"
    # list of tickers
    list_stock_ticker_folder = get_list_stock_ticker_in_folder(input_folder_name+"/210109")
    list_stock_ticker_folder2 = get_list_stock_ticker_in_folder(input_folder_name+"/210102")
    list_stock_ticker_file = get_list_stock_ticker_from_file(input_file_name)
    # read the file and save to a file
    str_today = str(pd.Timestamp.today().date())
    logging.info(f"Today is {str_today}")
    for stock_ticker in list_stock_ticker_file: 
        if False:
            # do only for one ticker
            if stock_ticker != "TSLA":
                continue
        already_have = stock_ticker in list_stock_ticker_folder
        logging.info(f"stock_ticker={stock_ticker}, already_have={already_have}")
        
        if False:
            #if already_have == True:
            str_date_start = get_first_day_of_stock_ticker(input_file_name_info, stock_ticker, add_outside_trading_hours, add_dividends_and_stocks_splits, auto_adjust)
            logging.info(f"str_date_start={str_date_start}")   
        
        # continue
        
        if already_have == False:
            logging.info(f"Create it until back to the latest folder, input_folder_name={input_folder_name}.")
            # deduce date from folder name
            folder_name = PurePath(input_folder_name).parts[-1]
            logging.info(f"folder_name={folder_name}")
            # from folder name deduce the date
            str_date_end = str(pd.to_datetime(f"20{folder_name[0:2]} {folder_name[2:4]} {folder_name[4:6]}"))
            logging.info(f"str_date_end={str_date_end}")
            #info_file = f"{}"
            str_date_start = get_first_day_of_stock_ticker(input_file_name_info, stock_ticker, add_outside_trading_hours, add_dividends_and_stocks_splits, auto_adjust)
            logging.info(f"str_date_start={str_date_start}")
            list_date = get_list_date(str_date_start, str_date_end)
            # now store in the previous folder
            do_store_all_period_to_file = True
            do_store_only_some_period_to_file = False
            df = get_df_from_list_date(stock_ticker, list_date, input_folder_name, period, add_outside_trading_hours,  add_dividends_and_stock_splits, auto_adjust, do_store_all_period_to_file, do_store_only_some_period_to_file)
            #return df
        continue
    
        # create list of dates
        if LIST_DATE is None:
            # find automatically the range that we want
            # we collect the data using the period max, then find the first date
            # than depending on that date build the LIST_DATE
            df = read_data(stock_ticker,
                   "max",
                   None,
                   None,
                   "1d",
                   ADD_OUTSIDE_TRADING_HOURS,
                   ADD_DIVIDENDS_AND_STOCK_SPLITS,
                   AUTO_ADJUST)
    
            # calculate list_date
            str_date_start = str(df.index[0].date())
            str_date_end = str_today
            logging.info(f"str_date_start={str_date_start}, str_date_end={str_date_end}")
            list_date = get_list_date(str_date_start, str_date_end)
        else:
            list_date = LIST_DATE
        for date in list_date:
            logging.info(f"{date}")
        
        do_store_all_period_to_file = False
        do_store_only_some_period_to_file = False
        df = get_df_from_list_date(stock_ticker, list_date, OUTPUT_FOLDER_NAME, PERIOD, ADD_OUTSIDE_TRADING_HOURS,  ADD_DIVIDENDS_AND_STOCK_SPLITS, AUTO_ADJUST, do_store_all_period_to_file, do_store_only_some_period_to_file)
    
        do_combine_with_previous_file = True   
        if do_combine_with_previous_file:
            logging.debug("Start do_combine_with_previous_file.")
            # retrieve the previous file
            date_start_all = "2019-01-01"
            date_end_all = "2021-01-01"
            suffix = "al"
            input_file_name_data = f"{OUTPUT_FOLDER_NAME}/df_{date_start_all}_{date_end_all}_{suffix}_{stock_ticker}.pickle"
            df__ = pd.read_pickle(input_file_name_data)
            logging.debug(f"Previous file {input_file_name_data} has {len(df__)} entries.")
    
            logging.debug("Start concatenating the old and new file")
            df_ = pd.concat([df__, df], axis = 0)
            logging.debug("Sort by index in chronolical order")
            df_.sort_index(inplace = True)
            logging.debug("Remove potential rare wrong values for after hours that are just to huge.")
            df_ = df_[df_.Close < 1e6] # eliminate sometimes very high wrong values
    
            # write to file
            date_end_all = str(LIST_DATE[-1][1].date())
            output_file_name_data = f"{OUTPUT_FOLDER_NAME}/df_{date_start_all}_{date_end_all}_{suffix}_{stock_ticker}.pickle"
            df_.to_pickle(output_file_name_data)
            logging.debug(f"Written final df_ with {len(df_)} elements to file {output_file_name_data}.")
    

def add_interval_with_open(df_):
    df = df_.reset_index()
    # after reset_index the order is datetime_end, then datetime_start
    # add an interval for the open value of each day, so that we can also visualize that
    l = []
    for i in df.index:
        if df.datetime_start[i].hour == 9 and df.datetime_start[i].minute == 30:
            row = df.iloc[i]
            l.append([
                    row["datetime_start"], # datetime_end
                    row["datetime_start"]  -  pd.Timedelta(1, unit = "m"), # datetime_start
                    row["Open"],
                    row["Open"],
                    row["Open"],
                    row["Open"],
                    0, 
                    ])
    # 
    df_open = pd.DataFrame(l, columns = list(df.columns))

    # concatenate the two
    df = pd.concat([df, df_open], axis = 0)

    # set index to one datetime and sort by index to integrate the open values at the right position
    my_datetime = "datetime_end"
    df.set_index(my_datetime, inplace = True) 
    df.sort_index(inplace = True)

    # ready to return
    return df

def apply_split(df, initial, final):
    # e.g. regular split as in TSLA on 2020-08-31: initial = 1 => final = 5
    # e.g. reverse split as in AMRH on 2020-12-31: initial = 4 => final = 1
    ratio = final / initial
    # prices must be divided by ratio
    # volumes mult be multiplied by ratio
    # datetime remeain the same
    for column in ["Open", "High", "Low", "Close"]:
        df[column] /= ratio
    for column in ["Volume"]:
        df[column] *= ratio
        
def get_df_pre_market(df):
    return df[(df.index.hour <= 8) | ((df.index.hour == 9) & (df.index.minute <= 30))]

def get_df_after_market(df):
    return df[(df.index.hour > 17) | ((df.index.hour == 16) & (df.index.minute > 0))]

def get_df_during_market(df):
    return df[((df.index.hour == 9) & (df.index.minute > 30))
              | ((df.index.hour > 9) & (df.index.hour < 16))
              | (df.index.hour == 16) & (df.index.minute == 0)]

def get_df_news(input_file_name_news, df):
    try:
        f = open(input_file_name_news)
        lines = f.readlines()
        counter = 0
        list_dict_news = []
        for line in lines:
            line = line.rstrip()
            if line == "":
                continue
            logging.debug(line)
            if counter%3 == 0:
                string_datetime = line
            if counter%3 == 1:
                text_short = line
            if counter%3 == 2:
                text_long = line
                # now the piece of news if finished
                my_string_datetime = string_datetime
                # if no time is present, but only the date, assume it is shortly before the market open at 9:30 am
                list_my_string_datetime = my_string_datetime.split(" ")
                if len(list_my_string_datetime) == 1 and (":" not in list_my_string_datetime):
                    my_string_datetime += " 09:15:00"
                datetime_end = pd.to_datetime(my_string_datetime).tz_localize(LOCALIZE_US_STOCK_MARKET)
                logging.debug(f"string_datetime={string_datetime}, datetime_end={datetime_end}")
                # find the numerical index in the df of the row whose datetime index is the closest to a given datetime
                i = np.argmin(np.abs(df.index - datetime_end))
                stock_close = df["Close"][i]
                stock_volume = df["Volume"][i]
                # stock_volume = np.max(df["Volume"].values) * 0.2
                list_dict_news.append(
                    {
                        "datetime_end": datetime_end,
                        "text_short": text_short,
                        "text_long": text_long,
                        "stock_price": stock_close,
                        "stock_volume": stock_volume,
                    }
                )
            counter += 1
        # create data frame and transform it into a time series by having the index as a datetime
        df_news = pd.DataFrame(list_dict_news).set_index("datetime_end")
        # sort by datetime
        df_news.sort_index(inplace = True)
    except IOError:
        raise RuntimeError(f"File {input_news_file_name} not accessible.")
    finally:
        f.close()
    return df_news
    
       
def plot_static(df, stock_ticker):
    # create a static plot with matplotlib
    # price at close (but with an added interval of 1 minute before trading to show also the price at Open)
    fig, ax =  plt.subplots(1, 1, figsize = (9, 6))
    ax.plot(df.Close, color = "lightgray", label = "Close")
    # plot markers on the plot for the points where one has to sell or buy
    # https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.plot.html
    # https://www.w3schools.com/python/matplotlib_markers.asp
    #
    plt.legend()
    plt.title(f"Stock price for {stock_ticker}", fontsize = 18)
    # plt.xticks(rotation="vertical")
    # date_form = DateFormatter("%H:%M:%S")
    date_form = DateFormatter("%Y-%m-%d")
    # date_form = DateFormatter("%m-%d")
    ax.xaxis.set_major_formatter(date_form)
    #ax.set_xticks(rotation='vertical')
    ax.tick_params(axis = "x", labelsize = 18, labelrotation = 90)
    plt.ylabel("Stock price [USD]", fontsize = 18)
    # plt.xlim(date_start, date_end)
    # plt.ylim(23.78, 35.82)

def plot_interactive(df, df_news = None, show_pre = True, show_after = True):
    # plot on an interactive plot using hvplot
    # https://hvplot.holoviz.org/user_guide/Customization.html
    # https://coderzcolumn.com/tutorials/data-science/how-to-convert-static-pandas-plot-matplotlib-to-interactive-hvplot#2

    # close
    df_during = get_df_during_market(df)
    df_during = add_interval_with_open(df_during)
    security_close = df_during.hvplot(
        x = "datetime_end",
        y = "Close",
        line_color = "lightgray",
        ylabel = "Stock price [USD]",
        xlabel = "Date",
        width = 900,
        height = 500,
        # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
        xlim = (df.index[0].tz_localize(None) - pd.Timedelta(60, "m"),
                 df.index[-1].tz_localize(None) + pd.Timedelta(60, "m")),
        # ylim = (100, 135),
        hover_cols = ["datetime_end", "Close", "Volume"],
        grid = True,
        )
    
    security_close_pre = get_df_pre_market(df).hvplot.scatter(
        x = "datetime_end",
        y = "Close",
        line_color = "brown",
        fill_color = "brown",
        ylabel = "Stock price [USD]",
        xlabel = "Date",
        width = 700,
        height = 350,
        # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
        # xlim = (df.index[0] - pd.Timedelta(1, "h"), df.index[-1] + pd.Timedelta(1, "h")),
        # ylim = (100, 135),
        # hover_cols = ["datetime_end", "Close", "Volume"],
        grid = True,
        )
    
    security_close_after = get_df_after_market(df).hvplot.scatter(
        x = "datetime_end",
        y = "Close",
        line_color = "darkblue",
        fill_color = "darkblue",
        ylabel = "Stock price [USD]",
        xlabel = "Date",
        width = 700,
        height = 350,
        # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
        # xlim = (df.index[0] - pd.Timedelta(1, "h"), df.index[-1] + pd.Timedelta(1, "h")),
        # ylim = (100, 135),
        # hover_cols = ["datetime_end", "Close", "Volume"],
        grid = True,
        )
    
    security_close_dots = df["Close"].hvplot.scatter(
        line_color = "darkgray",
        fill_color = "darkgray",
        ylabel = "Stock price [USD]",
        xlabel = "Date",
        width = 700,
        height = 350,
        # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
        # ylim = (25.45, 27.5),
        # hover_cols = ["datetime_end"],
        grid = True,
        )

    # news
    if df_news is not None:
        show_news = True
        news = df_news.hvplot.scatter(
            x = "datetime_end",
            y = "stock_price",
            color = "violet",
            # hover_cols = "all",
            hover_cols = ["text_short"],
            legend = True,
        )
    
    final_plot = security_close
    if show_pre:
        final_plot *= security_close_pre
    if show_after:
        final_plot *= security_close_after
    if show_news:
        final_plot *= news
        
    return final_plot


def plot_interactive_volume(df, df_news = None):
    volume = df["Volume"].hvplot.bar(
        # color = "orange",
        line_color = "orange",
        fill_color = "orange",
        width = 600,
        height = 400,
        hover_cols = ["Close"],
        )
    
    volume = df.hvplot.bar(
        x = "datetime_end",
        y = "Volume",
        # color = "orange",
        line_color = "orange",
        fill_color = "orange",
        width = 600,
        height = 400,
        hover_cols = ["Open", "Close", "Low", "High"],
        )
    
    # news but buggy, it shows some of the news at the right time
    # some news do not appear and some appear in the wrong place
    # probably due to the plotting in .bar format for the volume
    if df_news is not None:
        show_news = True
        # df_news["stock_volume"] = np.max(df.Volume.values) * 0.2
        # df_news["stock_volume"] = 10000
        news = df_news.hvplot.scatter(
            x = "datetime_end",
            y = "stock_volume",
            color = "black",
            # hover_cols = "all",
            hover_cols = ["text_short"],
            legend = True,
        )
    else:
        show_news = False

    final_plot = volume
    
    if show_news:
        final_plot *= news
    
    return final_plot
