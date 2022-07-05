# KMZ Extractor 

Script for KMZ file data extraction to Lat/Lon and dbZ values. 
Tailored for doppler weather radar files from Universidad de Guadalajara.

* Original Attribution: http://iam.cucei.udg.mx/sites/default/files/adjuntos/proyecto_-_equipo_3_1.pdf
* Radar Site: http://iam.cucei.udg.mx/radar/iam/

## Setup

### Prerequisites

- Python 3
- PIP 

Install the following modules: 

```
$ pip install numpy pandas Image pykml
```

### Usage 

```
usage: kmz_extractor.py [-h] [-f FILENAME] [-o OUTPUTFILENAME] [-k | --keepWorkDir | --no-keepWorkDir]

options:
  -h, --help            show this help message and exit
  -f FILENAME, --fileName FILENAME
                        The KMZ file you want to analyze
  -o OUTPUTFILENAME, --outputFileName OUTPUTFILENAME
                        The output name for the CSV file
  -k, --keepWorkDir, --no-keepWorkDir
                        Keep the workdir
```

### Run sample

```
$ python kmz_extractor.py -f sample.kmz
```



