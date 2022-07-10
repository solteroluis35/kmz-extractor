# SPDX-License-Identifier: MIT
'''Script for analyzing whether its hailing or not in the proximity of an address.'''

import statistics
import geopandas as gpd
import pandas as pd

HAIL_CHANCE_THRESHOLD = 0.70
DBZ_THRESHOLD = 33
ADDRESS = 'Guadalajara, Mexico'

location = gpd.tools.geocode(ADDRESS)
print('Calculating for', location)

# Read reflectivity data with geo location
reflectivity = pd.read_csv('reflectivity.csv')
geo_data_frame = gpd.GeoDataFrame(
    reflectivity, geometry=gpd.points_from_xy(reflectivity.lon, reflectivity.lat), crs='EPSG:4326')

storm_values = []
ranges = [1, 3, 5]  # 1Km, 3Km, 5Km
for i in ranges:
    geofence = location.to_crs(
        epsg=6372).buffer(i*1000).to_crs(epsg=4326)
    data_frame = pd.DataFrame(gpd.sjoin(geo_data_frame, gpd.GeoDataFrame(
        geometry=geofence), how='inner'))
    frame_sum = data_frame[data_frame['dBZ'] >=
                           DBZ_THRESHOLD].sum(axis=0, numeric_only=True)
    # The assumption is that 500 is a heavy storm dBZ sum
    read = frame_sum.dBZ / 500 / i
    storm_values.append(read)


print('Storm Values', storm_values)
storm_values[0] += storm_values[1]/3
storm_mean = statistics.mean(storm_values)
print('Avg:', storm_mean)

if storm_mean > HAIL_CHANCE_THRESHOLD:
    print('Chance of Hail, Take Cover!')
