from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, DataRange1d, Select
from bokeh.palettes import Blues4
from bokeh.plotting import figure, show
from datetime import timedelta
#from bokeh.io import output_notebook

import pandas as pd
from datetime import datetime
import numpy as np

#output_notebook()

def get_data(station_id, year):
    ''' Retrieves data from GHCN using the supplied station ID and year. 
    Returns a ColumnDataSource dataframe with record max/min, average max/min,
    and max/min for given year as well as left/right bounds for plotting later.
    '''
    df = pd.read_parquet(
        f"s3://noaa-ghcn-pds/parquet/by_station/STATION={station_id}/",
        storage_options={"anon": True},  # passed to `s3fs.S3FileSystem`
    )
    # Make date the index
    df['DATE'] = df['DATE'].apply(lambda x: datetime.strptime(x, '%Y%m%d'))
    df = df.set_index('DATE').sort_index()

    df_tmax = df.loc[df['ELEMENT'] == 'TMAX']
    df_tmin = df.loc[df['ELEMENT'] == 'TMIN']
    min_fixed = df_tmin[~((df_tmin.index.month==2)&(df_tmin.index.day==29))]
    max_fixed = df_tmax[~((df_tmax.index.month==2)&(df_tmax.index.day==29))]

    # Get records
    daily_min_records = (min_fixed['DATA_VALUE']/10.).groupby(
        [min_fixed.index.month, min_fixed.index.day]).min()
    daily_max_records = (max_fixed['DATA_VALUE']/10.).groupby(
        [max_fixed.index.month, max_fixed.index.day]).max()

    # Get averages
    daily_min_average = (min_fixed['DATA_VALUE']/10.).groupby(
        [min_fixed.index.month, min_fixed.index.day]).mean()
    daily_max_average = (max_fixed['DATA_VALUE']/10.).groupby(
        [max_fixed.index.month, max_fixed.index.day]).mean()

    # Get yearly values
    year = int(year)
    daily_min_year = (min_fixed[~(min_fixed.index.year<year)&
                        ~(min_fixed.index.year>year)])
    daily_max_year = (max_fixed[~(max_fixed.index.year<year)&
                        ~(max_fixed.index.year>year)])

    daily_min_year = daily_min_year['DATA_VALUE']/10.
    daily_max_year = daily_max_year['DATA_VALUE']/10.

    df = pd.DataFrame(columns=[])
    df['date'] = daily_min_year.index
    df['actual_min'] = daily_min_year.values
    df['actual_max'] = daily_max_year.values
    df['avg_min'] = daily_min_average.values
    df['avg_max'] = daily_max_average.values
    df['record_min'] = daily_min_records.values
    df['record_max'] = daily_max_records.values
    df['left'] = df.date - timedelta(days=0.5)
    df['right'] = df.date + timedelta(days=0.5)

    return ColumnDataSource(data=df)

def make_plot(source, title):
    ''' Creates Bokeh plot object '''
    plot = figure(x_axis_type="datetime", width=800, tools="", 
                    toolbar_location=None)
    plot.title.text = title
    plot.quad(top='record_max', bottom='record_min', left='left', right='right',
              color=Blues4[2], source=source, legend_label="Record")
    plot.quad(top='avg_max', bottom='avg_min', left='left', right='right',
              color=Blues4[1], source=source, legend_label="Average")
    plot.quad(top='actual_max', bottom='actual_min', left='left', right='right',
              color=Blues4[0], alpha=0.5, line_color="black", source=source, 
              legend_label="Actual")
    # fixed attributes
    plot.xaxis.axis_label = None
    plot.yaxis.axis_label = "Temperature (C)"
    plot.axis.axis_label_text_font_style = "bold"
    plot.x_range = DataRange1d(range_padding=0.0)
    plot.grid.grid_line_alpha = 0.3

    return plot

def update_plot(attrname, old, new):
    ''' Updates Bokehplot when inputs are changed '''
    city = city_select.value
    year = year_select.value
    plot.title.text = ("Weather data for " + cities[city]['title'] 
                        + ' ' + str(year))
    src = get_data(cities[city]['station_id'], year)
    source.data.update(src.data)

# City and year to display at start
city = 'Champaign'
year = '2023'

# List of available cities and station IDs
cities = {
    'Champaign': {
        'station_id': 'USC00118740',
        'title': 'Champaign, IL',
    },
    'Guam': {
        'station_id': 'GQW00041415',
        'title': 'Guam, GU',
    },
    'Fairbanks': {
        'station_id': 'USW00026411',
        'title': 'Fairbanks, AK',
    },
    'Chicago': {
        'station_id': 'USC00111577',
        'title': 'Chicago, IL',
    },
    'Atlanta': {
        'station_id': 'USW00013874',
        'title': 'Atlanta, GA',
    },
}

# Create list of years to select from
years_int = np.arange(1981, 2024, 1)
years = [str(x) for x in years_int]
# Create selections for dropdowns
city_select = Select(value=city, title='City', options=sorted(cities.keys()))
year_select = Select(value=year, title='Year', options=years)
# Call functions to retrieve data and make plots on start-up
source = get_data(cities[city]['station_id'], year)
plot = make_plot(source, "Weather data for " + cities[city]['title'] 
                + ' ' + str(year))
# Call update function when selections are changed
city_select.on_change('value', update_plot)
year_select.on_change('value', update_plot)
# Create dropdown menus
controls = column(city_select, year_select)

curdoc().add_root(row(plot, controls))
curdoc().title = "Weather"