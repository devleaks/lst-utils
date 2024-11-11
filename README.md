# Living Scenery Technology Utilities

Living Scenery Technology (LST) is a X-Plane plugin
to add life to your environment by moving objects
on paths.

LST comes with development utilities (converter, generator) but these tools are only available on windows platform.

This development is an attempt to provide the same tools in all environments
by using the scripting python language instead.

# Installation and Usage

Create a new python environment, activate it. Python above 3.10 requested.

Issue

```sh
pip install 'lst-utils @ git+https://github.com/devleaks/lst-utils.git'
```

This will install the following 3 client applications.

1. lst-converter-py
1. lst-generator-py
1. lst-geojson-py

# LST Converter

Application to partially convert older GroundTraffic.txt files to LST.

```
usage: lst-converter-py [-h] [ground_traffic_file]

Convert Ground Traffic file to LST

positional arguments:
  ground_traffic_file  Ground Traffic file to convert

options:
  -h, --help           show this help message and exit
```

# LST Generator

Application to generate LST files from X-Plane scenery files with coded conventions.

```
usage: lst-generator-py [-h] [--antimeridian] [scenery_folder]

Generate LST files from prepared scenery

positional arguments:
  scenery_folder  scenery folder

options:
  -h, --help      show this help message and exit
  --antimeridian  force bounding box around abtimeridian
```

# LST GeoJSON

Application to convert LST files to GeoJSON paths visible on geojson.io.

```
usage: lst-geojson-py [-h] [objects_file]

Convert LST Objects.lst file to GeoJSON features

positional arguments:
  objects_file  LST Objects.lst file to convert

options:
  -h, --help    show this help message and exit
```
