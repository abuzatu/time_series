import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, AutoMinorLocator
import datetime
import yfinance as yf
import hvplot.pandas
import logging

LOCALIZE_US_STOCK_MARKET = "America/New_York"

# logging level: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def update_df_1d(df, datetime):
    # this is for one day interval
    dt = df[datetime]
    date = None
    list_datetime_start = []
    list_datetime_end = []
    for i in range(len(df)):
        datetime_start = dt[i].tz_localize(LOCALIZE_US_STOCK_MARKET) + pd.Timedelta(9.5, unit = "h")
        datetime_end = datetime_start + pd.Timedelta(6.5, unit = "h") # there are 6.5 trading hours
        # print(f"i={i}, counter={counter}, datetime_start={datetime_start}, datetime_end={datetime_end}")
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
        # print(f"i={i}, counter={counter}, datetime_start={datetime_start}, datetime_end={datetime_end}")
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
        # print(f"i={i}, counter={counter}, datetime_start={datetime_start}, datetime_end={datetime_end}")
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
    
    # fix a bug in yfinance of not applying the localization when this option is on
    if add_outside_trading_hours:
        date_start += pd.Timedelta (5, "h")
        date_end += pd.Timedelta (5, "h")
    
    logger.debug(f"start read_data({stock_ticker}, {date_start}, {date_end}, {interval}")
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
    logging.debug(f"Load historical data into a data frame for {stock_ticker}, \
                  add_dividends_and_stock_splits={add_dividends_and_stock_splits}, \
                  auto_adjust={auto_adjust}")
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

def get_output_file_name(output_folder_name, date_start, date_end, interval, stock_ticker):
    return f"{output_folder_name}/df_{date_start}_{date_end}_{interval}_{stock_ticker}.pickle"

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
        print(f"File {input_news_file_name} not accessible.")
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
        height = 600,
        # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
        xlim = (df.index[0].tz_localize(None) - pd.Timedelta(60, "m"),
                 df.index[-1].tz_localize(None) + pd.Timedelta(60, "m")),
        # ylim = (100, 135),
        # hover_cols = ["datetime_end", "Close", "Volume"],
        grid = True,
        )
    
    security_close_pre = get_df_pre_market(df).hvplot.scatter(
        x = "datetime_end",
        y = "Close",
        line_color = "brown",
        fill_color = "brown",
        ylabel = "Stock price [USD]",
        xlabel = "Date",
        width = 800,
        height = 400,
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
        width = 800,
        height = 400,
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
        width = 800,
        height = 400,
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
