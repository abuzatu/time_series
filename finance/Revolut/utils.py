import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import logging

def read_file(input_file_name):
    file = open(input_file_name, "r")
    lines = file.readlines()
    for line in lines:
        line = line.rstrip()
        # print(line)
        list_el = line.split()
        if len(list_el) != 5:
            print(list_el)
        stock = float(list_el[2])
        price = float(list_el[3])
        cash = float(list_el[4])
        if ((stock * price) + cash) > 0.01:
            print(list_el)
        if ((stock * price) * cash) > 0:
            print(list_el)
            

# year: 2020 or 2021
def get_date(year, x):
    list_el = x.split("/")
    return pd.to_datetime(f"{year}-{list_el[0]}-{list_el[1]}")

# year: 2020 or 2021
def change_date(year, df):  
    df["date"] = df.date.map(lambda x: get_date(year, x))
    # df.set_index("date", inplace = True)
    return df

def get_df_trade(year):
    input_file_name = f"/Users/abuzatu/Work/data/finance/stocks/Revolut/Revolut_trades_{year}.txt"
    df = pd.read_csv(input_file_name, delimiter=" ")
    # check that stock and cash have opposite sign (when one is bougth, the other is sold
    # df["stock"] = df["stock"].astype(np.float64)
    df["multiply"] = df["stock"] * df["cash"]
    if len(df[df["multiply"] > 0.0]):
        print(df[df["multiply"] > 0.0])
        raise RuntimeError(f"Some instances where the stock and cash have opposite sign for year={year}")
    # the value cash should be used, as it takes into account also the fees paid for the trade
    # for the first few months I paid 1 euro per trade, plus the fee from SEC of 0.01$ per trade
    df["net"] = ((df["stock"] * df["price"]) + df["cash"]).map(lambda x: abs(x))
    if len(df[df["net"] > 2.0]):
        print(df[df["net"] > 2.0])
        raise RuntimeError(f"Some instances where the stock, price and cash disagree by more than 2$ for year={year}")
    #
    df = df.drop(["multiply", "net"], axis = 1)
    df = change_date(year, df)
    df["action"] = df["stock"].map(lambda x: "B" if x > 0 else "S")
    df["price_with_fees"] = abs(df["cash"] / df["stock"])
    df.loc[df["action"] == "B", "stock_left"] = df.loc[df["action"] == "B", "stock"]
    df.loc[df["action"] == "S", "realised_gain"] = 0.0
    df["counter"] = 1
    # df = df.sort_index()
    #
    return df

def update_df_trade_with_realised(df):
    for i in range(len(df)):
        row = df.iloc[i]
        if row["action"] == "B":
            continue
        # only rows with sales remain
        # now for a given sale, take if from the previous buys until there is nothing left
        stock_to_sell = abs(row["stock"])
        cash = row["cash"]
        ticker = row["ticker"]
        logging.debug(f"i={i}, stock_to_sell={stock_to_sell}")
        # now you do an action until there is nothing left, so a while loop
        nparray_stock_left = df["stock_left"].values
        nparray_price = df["price_with_fees"].values
        nparray_realised_gain = df["realised_gain"].values
        nparray_ticker = df["ticker"].values
        list_stock_sold_here = []
        list_price_sold_here = []
        list_cost_sold_here = []
        for j, stock_left in enumerate(nparray_stock_left):
            if nparray_ticker[j] != ticker:
                continue
            logging.debug(f"j={j}, stock_left={stock_left}")
            if np.isnan(stock_left):
                logging.debug(f"Skipping j={j} as NaN, as it is a buy")
            elif stock_left < 0:
                raise RuntimeError(f"stock_left is negative for j={j} stock_left={stock_left}")
            elif stock_left == 0:
                continue
            # we reach now cells with no zero values, all the cells with zero should be gone
            elif stock_to_sell <= stock_left:
                stock_sold_here = stock_to_sell
                list_stock_sold_here.append(stock_sold_here)
                price_sold_here = nparray_price[j]
                list_price_sold_here.append(price_sold_here)
                cost_sold_here = stock_sold_here * price_sold_here
                list_cost_sold_here.append(cost_sold_here)
                nparray_stock_left[j] = stock_left - stock_sold_here
                stock_to_sell = 0.0
                break
            else:
                # stock_to_sell is larger than the stock_left in this cell
                # so we sell this entire cell
                stock_sold_here = stock_left
                list_stock_sold_here.append(stock_sold_here)
                price_sold_here = nparray_price[j]
                list_price_sold_here.append(price_sold_here)
                cost_sold_here = stock_sold_here * price_sold_here
                list_cost_sold_here.append(cost_sold_here)
                nparray_stock_left[j] = 0.0 
                stock_to_sell = stock_to_sell - stock_sold_here
        logging.debug(f"i={i}")
        logging.debug(f"nparray_stock_left={nparray_stock_left}")
        logging.debug(f"list_stock_sold_here={list_stock_sold_here}")
        logging.debug(f"list_price_sold_here={list_price_sold_here}")
        logging.debug(f"list_cost_sold_here={list_cost_sold_here}")
        total_cost = sum(list_cost_sold_here)
        logging.debug(f"total_cost={total_cost}")
        realised_gain = cash - total_cost
        logging.debug(f"realised_gain={realised_gain}")
        nparray_realised_gain[i] = realised_gain
        df["stock_left"] = nparray_stock_left
        df["realised_gain"] = nparray_realised_gain
        df["stock_left_cost"] = df["stock_left"] * df["price_with_fees"]
    return df


def get_stock_left_breakeven_price(x):
    if (x == np.inf) or (x == np.NINF):
        result = np.nan
    elif x < 0:
        result = np.nan
    else:
        result = x
    return resut

def get_df_sum(df_trade):
    df_sum = df_trade.groupby("ticker").agg("sum")
    df_sum = df_sum.drop(["price", "price_with_fees"], axis = 1)
    # it gives scientific notation after sum, so let's write in digital format by rounding to 6 digits
    df_sum["stock"] = df_sum["stock"].map(lambda x: round(x, 8))
    df_sum["stock_left"] = df_sum["stock_left"].map(lambda x: round(x, 8))
    df_sum["stock_left_cost"] = df_sum["stock_left_cost"].map(lambda x: round(x, 8))
    # average price per current stock; when stock is no more held, return 0.0 instead of NaN
    df_sum["stock_left_average_price"] = (df_sum["stock_left_cost"] / df_sum["stock_left"]).fillna(0.0)#.map(lambda x: round(x, 2))
    # total real cost of the stocks I currently have
    # If all is well stock_left_real_cost is actually the opposite sign of cash
    df_sum["stock_left_real_cost"] = df_sum["stock_left_cost"] - df_sum["realised_gain"]
    # the stock price I need to sell to to have breakeven for the particular stock
    # if before realised gain, the breakeven price is smaller than the average price for current stocks
    # If before realised gain, the breakeven price is smaller than the average price for current stocks
    df_sum["stock_left_breakeven_price"] = (df_sum["stock_left_real_cost"] / df_sum["stock_left"]).map(lambda x: np.nan if ((x == np.inf) or (x == np.NINF) or (x<0)) else x).map(lambda x: round(x, 8))
    # rearrage columns
    df_sum = df_sum.loc[:, [
        "stock_left",
        "stock_left_average_price",
        "stock_left_breakeven_price",
        "stock_left_cost",
        "realised_gain",
        "stock_left_real_cost",
        "counter",
    ]]
    # df_sum["stock_left_breakeven_price"] = df_sum["stock_left_breakeven_price"].map(lambda x: round(x, 2))
    
    # df_sum = df_sum.sort_values(by="realised_gain", ascending=False)
    return df_sum