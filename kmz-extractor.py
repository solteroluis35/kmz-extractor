# SPDX-License-Identifier: MIT

import argparse
import os
import numpy as np
import pandas as pd
from zipfile import ZipFile
from PIL import Image
from pykml import parser
from shutil import copy, rmtree
import sys

WORK_DIR = 'workDir'
RADAR_IMAGE_FILE = 'radar.png'
KML_INFO_FILE = 'doc.kml'
SCRIPT_DIR = os.getcwd()
outputName = 'reflectivity'


argParser = argparse.ArgumentParser()
argParser.add_argument(
    "-f", "--fileName", help="The KMZ file you want to analyze")
argParser.add_argument("-o", "--outputFileName",
                       help="The output name for the CSV file")
argParser.add_argument("-k", "--keepWorkDir", help="Keep the workdir",
                       action=argparse.BooleanOptionalAction)
args = argParser.parse_args()


if args.outputFileName != None:
    outputName = args.outputFileName

# Get KMZ file
if args.fileName == None:
    kmzFile = input('KMZ Filename: ')
else:
    kmzFile = args.fileName

if not os.path.exists(WORK_DIR):
    os.makedirs(WORK_DIR)
copy(kmzFile, WORK_DIR)
os.chdir("./"+WORK_DIR)

# Uncompress KMZ
nom, ext = os.path.splitext(kmzFile)
os.rename(kmzFile, nom + ".zip")
zipFile = nom + ".zip"

with ZipFile(file=zipFile, mode="r", allowZip64=True) as file:
    archivo = file.open(name=file.namelist()[0], mode="r")
    archivo.close()
    print("Uncompressing")
    file.extractall(path=os.curdir)

    extractedImage = next(
        filter(lambda file: file.endswith(".png"), os.listdir()))
    os.rename(extractedImage, RADAR_IMAGE_FILE)

# Get array from image
print('Getting RGBA matrix')
imageArray = np.array(Image.open(RADAR_IMAGE_FILE))


# Get KML file reference coordinates
print('Getting coordinates')
with open(KML_INFO_FILE, 'r') as kml:
    root = parser.parse(kml).getroot()

north = root.Folder.GroundOverlay.LatLonBox.north.text
south = root.Folder.GroundOverlay.LatLonBox.south.text
east = root.Folder.GroundOverlay.LatLonBox.east.text
west = root.Folder.GroundOverlay.LatLonBox.west.text

# Calculate reflectiviy
print('Calculating reflectivity values')
redRing = np.array([[0, 0]])

# Delete redRing
for i in np.arange(0, np.size(imageArray, 0)):
    for j in np.arange(0, np.size(imageArray, 1)):
        if imageArray[i, j, 3] == 255:
            A = np.array([[i, j]])
            redRing = np.concatenate((redRing, A))
redRing = np.delete(redRing, 0, 0)

for i in np.arange(0, np.size(redRing, 0)):
    imageArray[redRing[i, 0], redRing[i, 1], 3] = 0

filteredImageArray = np.array([[0, 0, 0, 0, 0]])

# Remove null entries
for i in np.arange(0, np.size(imageArray, 0)):
    for j in np.arange(0, np.size(imageArray, 1)):
        if imageArray[i, j, 3] != 0:
            A = np.array(
                [[imageArray[i, j, 0], imageArray[i, j, 1], imageArray[i, j, 2], i, j]])
            filteredImageArray = np.concatenate((filteredImageArray, A))
filteredImageArray = np.delete(filteredImageArray, 0, 0)

# Reference points
referencePoints = np.array([[255, 255, 255, 78], [255, 225, 255, 73], [255, 200, 255, 68],
                            [255, 128, 255, 63], [
                                255, 0, 255, 58], [255, 0, 100, 53],
                            [255, 0, 0, 48], [255, 85, 0, 43], [255, 170, 0, 38],
                            [255, 200, 0, 33], [
                                255, 255, 0, 28], [0, 150, 50, 23],
                            [0, 175, 0, 18], [0, 255, 0, 13], [0, 255, 128, 10],
                            [0, 255, 255, -10], [0, 0, 255, -31.5]])

# Distance between reference points
referencePointsDistance = np.zeros(16)
for i in np.arange(0, 16):
    referencePointsDistance[i] = np.sqrt((referencePoints[i+1, 1] - referencePoints[i, 1])
                                         ** 2 + (referencePoints[i+1, 2] - referencePoints[i, 2]) ** 2)

# dbZ variation between reference points
referencePointsVariation = np.zeros(16)
for i in np.arange(0, 16):
    referencePointsVariation[i] = referencePoints[i,
                                                  3] - referencePoints[i+1, 3]

 # Lineal factors
linealFactors = np.zeros(16)
for i in np.arange(0, 16):
    linealFactors[i] = referencePointsVariation[i]/referencePointsDistance[i]

    # RGB to dBZ function
    def rgbToDbZ(red, green, blue):
        if red <= 30:
            array = np.zeros(6)
            for i in np.arange(11, 17):
                array[i - 11] = np.sqrt((green-referencePoints[i, 1])
                                        ** 2 + (blue-referencePoints[i, 2]) ** 2)

            laDistance = min(array)
            laIndex = np.where(array == laDistance)[0][0]
            array = np.delete(array, laIndex)
            lbDistance = min(array)
            lbIndex = np.where(array == lbDistance)[0][0]

            if laIndex == 0:
                assignedReflectivity = referencePoints[11,
                                                       3] - (linealFactors[11]) * laDistance
            elif laIndex == 5:
                assignedReflectivity = referencePoints[16,
                                                       3] + (linealFactors[15]) * laDistance
            else:
                if lbIndex == laIndex:
                    assignedReflectivityWithLaDistance = referencePoints[11+laIndex, 3] - \
                        (linealFactors[11 + laIndex]) * laDistance
                    assignedReflectivityWithLbDistance = referencePoints[12+laIndex, 3] + \
                        (linealFactors[11 + laIndex]) * lbDistance
                    assignedReflectivity = (
                        assignedReflectivityWithLaDistance+assignedReflectivityWithLbDistance)/2
                else:
                    assignedReflectivityWithLaDistance = referencePoints[11+laIndex, 3] + \
                        (linealFactors[10 + laIndex]) * laDistance
                    assignedReflectivityWithLbDistance = referencePoints[10+laIndex, 3] - \
                        (linealFactors[10 + laIndex]) * lbDistance
                    assignedReflectivity = (
                        assignedReflectivityWithLaDistance+assignedReflectivityWithLbDistance)/2

        if red >= 225:
            array = np.zeros(11)
            for i in np.arange(0, 11):
                array[i] = np.sqrt((green-referencePoints[i, 1]) **
                                   2 + (blue-referencePoints[i, 2]) ** 2)

            laDistance = min(array)
            laIndex = np.where(array == laDistance)[0][0]
            array = np.delete(array, laIndex)
            lbDistance = min(array)
            lbIndex = np.where(array == lbDistance)[0][0]

            if laIndex == 10:
                assignedReflectivity = referencePoints[10,
                                                       3] + (linealFactors[9]) * laDistance
            elif laIndex == 0:
                assignedReflectivity = referencePoints[0,
                                                       3] - (linealFactors[0]) * laDistance
            else:
                if lbIndex == laIndex:
                    assignedReflectivityWithLaDistance = referencePoints[laIndex, 3] - (
                        linealFactors[laIndex]) * laDistance
                    assignedReflectivityWithLbDistance = referencePoints[laIndex+1, 3] + (
                        linealFactors[laIndex]) * lbDistance
                    assignedReflectivity = (
                        assignedReflectivityWithLaDistance+assignedReflectivityWithLbDistance)/2
                else:
                    assignedReflectivityWithLaDistance = referencePoints[laIndex, 3] + (
                        linealFactors[laIndex - 1]) * laDistance
                    assignedReflectivityWithLbDistance = referencePoints[laIndex - 1, 3] - \
                        (linealFactors[laIndex - 1]) * lbDistance
                    assignedReflectivity = (
                        assignedReflectivityWithLaDistance+assignedReflectivityWithLbDistance)/2
        return assignedReflectivity

    dbzMatrix = np.zeros((np.size(filteredImageArray, 0), 3))
    for i in np.arange(0, np.size(filteredImageArray, 0)):
        dbzMatrix[i, 0] = rgbToDbZ(
            filteredImageArray[i, 0], filteredImageArray[i, 1], filteredImageArray[i, 2])
        dbzMatrix[i, 1] = filteredImageArray[i, 3]
        dbzMatrix[i, 2] = filteredImageArray[i, 4]

    # Assign coordinates
    north, south, east, west = float(north), float(
        south), float(east), float(west)

    dvertical = (north-south)/np.size(imageArray, 0)
    dhorizontal = (east-west)/np.size(imageArray, 1)

    # Scaled matrix
    reflectivityArray = np.zeros((np.size(filteredImageArray, 0), 3))
    for k in np.arange(0, np.size(dbzMatrix, 0)):
        reflectivityArray[k, 0] = round(dbzMatrix[k, 0], 1)
        reflectivityArray[k, 1] = north - (dbzMatrix[k, 1] + 1/2) * dvertical
        reflectivityArray[k, 2] = west + (dbzMatrix[k, 2] + 1/2) * dhorizontal

# Export Matrix
print('Exporting Data')

dataFrame = pd.DataFrame(reflectivityArray)
dataFrame.to_csv(outputName+'.csv')

if args.keepWorkDir == None:
    copy(outputName+'.csv', SCRIPT_DIR)
    rmtree(SCRIPT_DIR + "/" + WORK_DIR)

print('Done.')
