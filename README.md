# Living Scenery Technology Utilities

Living Scenery Technology (LST) is a X-Plane plugin
to add life to your environment by moving objects
on paths.

LST comes with development utilities (converter, generator) but these tools are only available on windows platform.

This development is an attempt to provide the same tools in all environments
by using the scripting python language instead.

# Installation and Usage

Create a new python environment, activate it. Python above 3.10 recommanded.

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

# LST Generator

Application to generate LST files from X-Plane scenery files with coded conventions.

# LST GeoJSON

Application to convert LST files to GeoJSON paths visible on geojson.io.

