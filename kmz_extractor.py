# SPDX-License-Identifier: MIT
'''Script for KMZ file data extraction to Lat/Lon and dbZ values.'''

import argparse
import os
from zipfile import ZipFile
from shutil import copy, rmtree
import numpy as np
import pandas as pd
from PIL import Image
from pykml import parser

WORK_DIR = 'workDir'
RADAR_IMAGE_FILE = 'radar.png'
KML_INFO_FILE = 'doc.kml'
SCRIPT_DIR = os.getcwd()

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    '-f', '--fileName', help='The KMZ file you want to analyze')
arg_parser.add_argument('-o', '--outputFileName',
                        help='The output name for the CSV file')
arg_parser.add_argument('-k', '--keepWorkDir', help='To keep the workdir',
                        action=argparse.BooleanOptionalAction)
args = arg_parser.parse_args()


if args.outputFileName is not None:
    OUTPUT_NAME = args.outputFileName
else:
    OUTPUT_NAME = 'reflectivity'

# Get KMZ file
if args.fileName is None:
    kmzFile = input('KMZ Filename: ')
else:
    kmzFile = args.fileName

if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)
copy(kmzFile, WORK_DIR)
os.chdir('./'+WORK_DIR)

# Uncompress KMZ
name, ext = os.path.splitext(kmzFile)
os.rename(kmzFile, name + '.zip')
zip_file = name + '.zip'

with ZipFile(file=zip_file, mode='r', allowZip64=True) as file:
    print('Uncompressing')
    file.extractall(path=os.curdir)

    extracted_image = next(
        filter(lambda file: file.endswith('.png'), os.listdir()))
    os.rename(extracted_image, RADAR_IMAGE_FILE)

# Get array from image
print('Getting RGBA matrix')
image_array = np.array(Image.open(RADAR_IMAGE_FILE))


# Get KML file reference coordinates
print('Getting coordinates')
with open(KML_INFO_FILE, 'r', encoding='utf8') as kml:
    root = parser.parse(kml).getroot()

north = root.Folder.GroundOverlay.LatLonBox.north.text
south = root.Folder.GroundOverlay.LatLonBox.south.text
east = root.Folder.GroundOverlay.LatLonBox.east.text
west = root.Folder.GroundOverlay.LatLonBox.west.text

# Calculate reflectiviy
print('Calculating reflectivity values')
red_ring = np.array([[0, 0]])

# Delete redRing
for i in np.arange(0, np.size(image_array, 0)):
    for j in np.arange(0, np.size(image_array, 1)):
        if image_array[i, j, 3] == 255:
            A = np.array([[i, j]])
            red_ring = np.concatenate((red_ring, A))
red_ring = np.delete(red_ring, 0, 0)

for i in np.arange(0, np.size(red_ring, 0)):
    image_array[red_ring[i, 0], red_ring[i, 1], 3] = 0

filtered_image_array = np.array([[0, 0, 0, 0, 0]])

# Remove null entries
for i in np.arange(0, np.size(image_array, 0)):
    for j in np.arange(0, np.size(image_array, 1)):
        if image_array[i, j, 3] != 0:
            A = np.array(
                [[image_array[i, j, 0], image_array[i, j, 1], image_array[i, j, 2], i, j]])
            filtered_image_array = np.concatenate((filtered_image_array, A))
filtered_image_array = np.delete(filtered_image_array, 0, 0)

# Reference points
reference_points = np.array(
    [
        [255, 255, 255, 78],
        [255, 225, 255, 73],
        [255, 200, 255, 68],
        [255, 128, 255, 63],
        [255, 0, 255, 58],
        [255, 0, 100, 53],
        [255, 0, 0, 48],
        [255, 85, 0, 43],
        [255, 170, 0, 38],
        [255, 200, 0, 33],
        [255, 255, 0, 28],
        [0, 150, 50, 23],
        [0, 175, 0, 18],
        [0, 255, 0, 13],
        [0, 255, 128, 10],
        [0, 255, 255, -10],
        [0, 0, 255, -31.5]
    ]
)

# Distance between reference points
reference_points_distance = np.zeros(16)
for i in np.arange(0, 16):
    reference_points_distance[i] = np.sqrt((reference_points[i+1, 1] - reference_points[i, 1])
                                           ** 2 + (reference_points[i+1, 2] -
                                                   reference_points[i, 2]) ** 2)

# dbZ variation between reference points
reference_points_variation = np.zeros(16)
for i in np.arange(0, 16):
    reference_points_variation[i] = reference_points[i,
                                                     3] - reference_points[i+1, 3]

 # Lineal factors
lineal_factors = np.zeros(16)
for i in np.arange(0, 16):
    lineal_factors[i] = reference_points_variation[i] / \
        reference_points_distance[i]

    def rgb_to_dbz(red, green, blue):
        '''RGB to dBZ function'''
        if red <= 30:
            array = np.zeros(6)
            for i in np.arange(11, 17):
                array[i - 11] = np.sqrt((green-reference_points[i, 1])
                                        ** 2 + (blue-reference_points[i, 2]) ** 2)

            la_distance = min(array)
            la_index = np.where(array == la_distance)[0][0]
            array = np.delete(array, la_index)
            lb_distance = min(array)
            lb_index = np.where(array == lb_distance)[0][0]

            if la_index == 0:
                assigned_reflectivity = (
                    reference_points[11, 3]
                    - (lineal_factors[11]) * la_distance
                )
            elif la_index == 5:
                assigned_reflectivity = (
                    reference_points[16, 3]
                    + (lineal_factors[15]) * la_distance
                )
            else:
                if lb_index == la_index:
                    assigned_reflectivity_with_la_distance = (
                        reference_points[11+la_index, 3]
                        - (lineal_factors[11 + la_index]) * la_distance
                    )
                    assigned_reflectivity_with_lb_distance = (
                        reference_points[12+la_index, 3]
                        + (lineal_factors[11 + la_index]) * lb_distance
                    )
                    assigned_reflectivity = (
                        assigned_reflectivity_with_la_distance
                        + assigned_reflectivity_with_lb_distance
                    ) / 2
                else:
                    assigned_reflectivity_with_la_distance = (
                        reference_points[11+la_index, 3]
                        + (lineal_factors[10 + la_index]) * la_distance
                    )
                    assigned_reflectivity_with_lb_distance = (
                        reference_points[10+la_index, 3]
                        - (lineal_factors[10 + la_index]) * lb_distance
                    )
                    assigned_reflectivity = (
                        assigned_reflectivity_with_la_distance
                        + assigned_reflectivity_with_lb_distance
                    ) / 2

        if red >= 225:
            array = np.zeros(11)
            for i in np.arange(0, 11):
                array[i] = np.sqrt((green-reference_points[i, 1]) **
                                   2 + (blue-reference_points[i, 2]) ** 2)

            la_distance = min(array)
            la_index = np.where(array == la_distance)[0][0]
            array = np.delete(array, la_index)
            lb_distance = min(array)
            lb_index = np.where(array == lb_distance)[0][0]

            if la_index == 10:
                assigned_reflectivity = (
                    reference_points[10, 3]
                    + (lineal_factors[9]) * la_distance
                )
            elif la_index == 0:
                assigned_reflectivity = (
                    reference_points[0, 3]
                    - (lineal_factors[0]) * la_distance
                )
            else:
                if lb_index == la_index:
                    assigned_reflectivity_with_la_distance = (
                        reference_points[la_index, 3]
                        - (lineal_factors[la_index]) * la_distance
                    )
                    assigned_reflectivity_with_lb_distance = (
                        reference_points[la_index+1, 3]
                        + (lineal_factors[la_index]) * lb_distance
                    )
                    assigned_reflectivity = (
                        assigned_reflectivity_with_la_distance
                        + assigned_reflectivity_with_lb_distance
                    ) / 2
                else:
                    assigned_reflectivity_with_la_distance = (
                        reference_points[la_index, 3]
                        + (lineal_factors[la_index - 1]) * la_distance
                    )
                    assigned_reflectivity_with_lb_distance = (
                        reference_points[la_index - 1, 3]
                        - (lineal_factors[la_index - 1]) * lb_distance
                    )
                    assigned_reflectivity = (
                        assigned_reflectivity_with_la_distance +
                        assigned_reflectivity_with_lb_distance
                    ) / 2
        return assigned_reflectivity

    dbz_matrix = np.zeros((np.size(filtered_image_array, 0), 3))
    for i in np.arange(0, np.size(filtered_image_array, 0)):
        dbz_matrix[i, 0] = rgb_to_dbz(
            filtered_image_array[i, 0],
            filtered_image_array[i, 1],
            filtered_image_array[i, 2]
        )
        dbz_matrix[i, 1] = filtered_image_array[i, 3]
        dbz_matrix[i, 2] = filtered_image_array[i, 4]

    # Assign coordinates
    north, south, east, west = float(north), float(
        south), float(east), float(west)

    dvertical = (north-south)/np.size(image_array, 0)
    dhorizontal = (east-west)/np.size(image_array, 1)

    # Scaled matrix
    reflectivity_array = np.zeros((np.size(filtered_image_array, 0), 3))
    for k in np.arange(0, np.size(dbz_matrix, 0)):
        reflectivity_array[k, 0] = round(dbz_matrix[k, 0], 1)
        reflectivity_array[k, 1] = north - (dbz_matrix[k, 1] + 1/2) * dvertical
        reflectivity_array[k, 2] = west + \
            (dbz_matrix[k, 2] + 1/2) * dhorizontal

# Export Matrix
print('Exporting Data')

data_frame = pd.DataFrame(reflectivity_array, columns=['dBZ','lat','lon'])
data_frame.to_csv(OUTPUT_NAME+'.csv',index=False)

if args.keepWorkDir is None:
    copy(OUTPUT_NAME+'.csv', SCRIPT_DIR)
    rmtree(SCRIPT_DIR + '/' + WORK_DIR)

print('Done.')
