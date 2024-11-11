import sys
import os
import json
import argparse


# @todo: add reading of init.lst and read bounding box
#
class LSTGeoJSON:

    def __init__(self, filename: str):
        self.filename = filename

    def init(self):
        pass

    def convert(self):
        def get_line(file_pointer):
            line = file_pointer.readline()
            if line == "":
                return None
            return line.strip()

        features = []
        scan_ok = False
        line = None
        line_num = 0

        fp = open(self.filename, "r")
        line = get_line(fp)
        line_num = line_num + 1

        while line is not None and line_num < 1000:
            args = line.split(",")
            latest_name = "noname"

            if line.startswith("LOOP"):
                latest_cmd = "train"
                latest_startline = line_num
                scan_ok = True

            elif line.startswith("TRAIN"):
                latest_cmd = "train"
                latest_name = args[1]
                latest_startline = line_num
                scan_ok = True

            elif line.startswith("HIGHWAY"):
                latest_cmd = "highway"
                latest_name = args[1]
                latest_startline = line_num
                scan_ok = True

            if scan_ok:
                curr_coords = []
                line = get_line(fp)
                line_num = line_num + 1
                while line is not None and line != "":
                    if line.startswith("WP,"):
                        args = line.split(",")
                        if len(args) > 3:
                            curr_coords.append([float(args[2]), float(args[1])])
                    line = get_line(fp)
                    line_num = line_num + 1

                scan_ok = False

                features.append({
                    "type": "Feature",
                    "properties": {
                        "filename": self.filename,
                        "lineno": latest_startline,
                        "type": latest_cmd,
                        "name": latest_name
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": curr_coords
                    }
                })

            else:
                pass

            line = get_line(fp)
            line_num = line_num + 1

        fp.close()

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def print(self):
        print(json.dumps(self.convert(), indent=2))

    def save(self, root = None):
        if root is None:
            fn = self.filename.replace(".lst", "").replace(".LST", "")
            args = os.path.split(fn)
            root = args[1]
        with open(os.path.join(args[0], root+".geojson"), "w") as fp:
            fp.write(json.dumps(self.convert(), indent=2))
        print(f"{root+'.geojson'} created")


def main():
    # Command-line arguments
    #
    parser = argparse.ArgumentParser(description="Convert LST Objects.lst file to GeoJSON features")
    parser.add_argument("objects_file", metavar="objects_file", type=str, nargs="?", default="Objects.lst", help="LST Objects.lst file to convert")

    args = parser.parse_args()
    fn=args.objects_file

    if fn is None:
        parser.print_help()
        sys.exit(1)

    gt = LSTGeoJSON(fn)

    # To view transformation on terminal, uses:
    # gt.print()
    #

    # To save in init-filename.lst and objects-filename.txt use
    gt.save()
    #

    # To save in init.lst and objects.txt use
    # gt.save("")
    #
    # Default python debugging in INFO, use DEBUG if you need.
    # Set it at begining of this file.
    #

if __name__ == '__main__':
    main()