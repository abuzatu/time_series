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
              date_initial_data,
              date_final_data,
              interval,
              add_outside_trading_hours,
              add_dividends_and_stock_splits,
              auto_adjust):

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
    ticker = yf.Ticker(stock_ticker)
    
    df_original = ticker.history(
        period = period,
        start = date_initial_data, 
        end = date_final_data, 
        interval = interval, 
        prepost = add_outside_trading_hours,
        actions = add_dividends_and_stock_splits,
        auto_adjust = auto_adjust,
        )

    if len(df_original) == 0:
        return df_original

    # For the 1h interval, there is a bug as it returns a date without the time, so we need to add by hand
    # There are 7 intervals for every day, sometimes fewer if there is a short day
    # The stock market usually starts at 9:30 am and ends at 5 pm.
    # so the last interval has only 30 minutes.
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
    df = df[["datetime_start", "datetime_end", "Open", "High", "Low", "Close", "Volume"]]

    # add an interval for the open value of each day, so that we can also visualize that
    l = []
    for i in df.index:
        if df.datetime_start[i].hour == 9 and df.datetime_start[i].minute == 30:
            row = df.iloc[i]
            l.append([
                    row["datetime_start"]  -  pd.Timedelta(1, unit = "m"),
                    row["datetime_start"],
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

def plot_interactive(df):
    # plot on an interactive plot using hvplot
    # https://hvplot.holoviz.org/user_guide/Customization.html
    # https://coderzcolumn.com/tutorials/data-science/how-to-convert-static-pandas-plot-matplotlib-to-interactive-hvplot#2

    # close
    security_close = df["Close"].hvplot(
        line_color = "lightgray",
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

    final_plot = security_close
    return final_plot

def plot_interactive_volume(df):

    volume = df["Volume"].hvplot.bar(
        # color = "orange",
        line_color = "orange",
        fill_color = "orange",
        width = 850,
        height = 300,
        )

    final_plot_volume = volume
    return final_plot_volume
