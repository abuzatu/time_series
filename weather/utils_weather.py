import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import datetime
import hvplot.pandas

# example to rename just one column in a data frame
# df.columns = ["wind_speeed" if x == "windspeed" else x for x in df.columns]

# when saving to csv, do not store the index too
# df.to_csv("/Users/abuzatu/Work/data/weather/weather.csv", index = False)

def get_concat_df(
    input_folder_name: str,
    list_file: str,
) -> pd.DataFrame:
    '''
    Retrieves data frames of the same format from a list of files and concatenates them.
    '''
    list_df = []
    for file in list_file:
        file_name = f"{input_folder_name}/{file}"
        list_df.append(pd.read_csv(file_name))
    df = pd.concat(list_df, axis = 0)
    return df

def check_df_for_null_values(
    df: pd.DataFrame,
):
    '''
    Check each column for null values.
    '''
    # no missing data
    for column in df.columns:
        nb_total = len(df[column])
        nb_empty = sum(df[column].isnull())
        nb_filled = nb_total - nb_empty
        print(f"{column}: filled={nb_filled}/{nb_total}, empty={nb_empty}/{nb_total}.")

def plot_static_line(
    df: pd.DataFrame,
    list_var_unit: list
):
    '''
    Create static plot overlaying several variables, their units are also mentioned.
    '''
    fig, ax = plt.subplots(figsize=(8, 6))
    for var, unit in list_var_unit:
        ax.plot(df[var], label = f"{var} [{unit}]")
    date_form = DateFormatter("%Y-%m-%d")
    ax.xaxis.set_major_formatter(date_form)
    plt.legend()
    plt.xticks(rotation="vertical")
    plt.xlabel("Time", fontsize=16)
    plt.ylabel(f"Variable", fontsize=16)
    plt.title(f"Time series", fontsize=16)
    
def plot_static_scatter(
    df: pd.DataFrame,
    list_var_unit: list
):
    
    if len(list_var_unit) != 2:
        raise RuntimeError("There should be two elements for a scatter plot in list_var_unit={list_var_unit}!")
        
    var_x, unit_x = list_var_unit[0]
    var_y, unit_y = list_var_unit[1]
    
    plt.scatter(df[var_x], df[var_y])
    plt.xlabel(f"{var_x} [{unit_x}]")
    plt.ylabel(f"{var_y} [{unit_y}]")    
    
def plot_interactive_line(
    df: pd.DataFrame,
    list_var_unit: list
):
    # plot on an interactive plot using hvplot
    # https://hvplot.holoviz.org/user_guide/Customization.html
    # https://coderzcolumn.com/tutorials/data-science/how-to-convert-static-pandas-plot-matplotlib-to-interactive-hvplot#2
    
    list_color = ["red", "blue", "green", "orange"]
    final_plot = None
    for i, (var, unit) in enumerate(list_var_unit):
        ylabel = f"{var} [{unit}]"
        my_plot = df.hvplot(
            # x = "datetime",
            y = var,
            line_color = list_color[i],
            ylabel = ylabel,
            xlabel = "Date",
            title = ylabel,
            width = 900,
            height = 600,
            # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
            #xlim = (df.index[0].tz_localize(None) - pd.Timedelta(60, "m"),
            #         df.index[-1].tz_localize(None) + pd.Timedelta(60, "m")),
            # ylim = (100, 135),
            # hover_cols = ["datetime_end", "Close", "Volume"],
            grid = True,
            legend = True,
            hover_cols = "all",
            )
        if i == 0:
            final_plot = my_plot
        else:
            final_plot *= my_plot
        
    return final_plot

def plot_interactive_scatter(
    df: pd.DataFrame,
    list_var_unit: list,
    color: str = "darkgray",
):
    # plot on an interactive plot using hvplot
    # https://hvplot.holoviz.org/user_guide/Customization.html
    # https://coderzcolumn.com/tutorials/data-science/how-to-convert-static-pandas-plot-matplotlib-to-interactive-hvplot#2
    
    if len(list_var_unit) != 2:
        raise RuntimeError("There should be two elements for a scatter plot in list_var_unit={list_var_unit}!")
        
    var_x, unit_x = list_var_unit[0]
    var_y, unit_y = list_var_unit[1]
    xlabel = f"{var_x} [{unit_x}]"
    ylabel = f"{var_x} [{unit_x}]"
        
    final_plot = None

    final_plot = df.hvplot.scatter(
            x = var_x,
            y = var_y,
            line_color = color,
            fill_color = color,
            xlabel = xlabel,
            ylabel = ylabel,
            title = f"{xlabel} vs {ylabel}",
            width = 900,
            height = 600,
            # xlim = (DATE_INITIAL_PLOT, DATE_FINAL_PLOT),
            #xlim = (df.index[0].tz_localize(None) - pd.Timedelta(60, "m"),
            #         df.index[-1].tz_localize(None) + pd.Timedelta(60, "m")),
            # ylim = (100, 135),
            # hover_cols = ["datetime_end", "Close", "Volume"],
            grid = True,
            legend = True,
            #hover_cols = "all",
            )
        
    return final_plot