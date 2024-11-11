# GroundTraffic to Living Scenery Technology converter
#
# Usage
#
# python gt2lst.py groundtrafficfile.txt
#
# converts groundtrafficfile.txt and produces 2 LST files:
# init-groundtrafficfile.txt.lst
# objects.groundtrafficfile.txt.lst
#
# See adjustments at end of this file.
#
import logging
import sys
import os
import json
import argparse
from math import copysign, sin, cos, atan2, sqrt, radians
from datetime import datetime
from biglib import BigLib, XPLANE_ROOT_PATH

__START_YEAR__ = 2023  # of this project
__THIS_YEAR__ = datetime.now().year
__NAME__ = "gt2lst"
__DESCRIPTION__ = "GroundTraffic to Living Scenery Technology Converter"
__LICENSE__ = "MIT"
__LICENSEURL__ = "https://mit-license.org"
__COPYRIGHT__ = f"© {__START_YEAR__}{'-' + str(__THIS_YEAR__) if __THIS_YEAR__ > __START_YEAR__ else ''} Pierre M <pierre@devleaks.be>"
__version__ = "0.3.2"
__version_info__ = tuple(map(int, __version__.split(".")))
__version_name__ = "development"
__authorurl__ = "https://github.com/devleaks/gt2lst"


DEFAULT_OBJECT = "gt2lst/follow_me.obj"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gt2lst")


# Command-line arguments
#
parser = argparse.ArgumentParser(description="Convert Ground Traffic file to LST")
parser.add_argument("ground_traffic_file", metavar="ground_traffic_file", type=str, nargs="?", default="GroundTraffic.txt", help="Ground Traffic file to convert")

# GT uses "distance" between objects, LST uses "time" between objects.
def get_time(speed, distance):
    # speed in km/h, distance in meters, return seconds
    return distance / (speed * 3600)


def get_distance(speed, time):
    # speed in km/h, time in seconds, returns meters
    return time * speed / 3.6


R = 6373.0


def distance(lat1_d, lon1_d, lat2_d, lon2_d):
    lat1 = radians(lat1_d)
    lon1 = radians(lon1_d)
    lat2 = radians(lat2_d)
    lon2 = radians(lon2_d)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def total_length(ls):
    total = 0
    end = len(ls) - 1
    for i in range(end):
        total = total + distance(ls[i][1], ls[i][0], ls[i + 1][1], ls[i + 1][0])
    return total


class Converter:
    def __init__(self, **kwargs):
        self.line_num = kwargs.get("line_num")
        self.out = []
        self.ls_points = []

    def reset(self):
        self.out = []
        self.ls_points = []

    def nl(self):
        self.out.append("")

    def comment(self, line):
        self.out.append("# " + line)

    def line(self, line):
        self.out.append(line)

    def append(self, lines):
        self.out = self.out + lines

    def get(self):
        return self.out

    def print(self):
        print("\n".join(self.out))


class Condition(Converter):
    def __init__(self, obj: str, val1, val2, **kwargs):
        Converter.__init__(self, **kwargs)
        self.obj = obj
        self.val1 = val1
        self.val2 = val2
        self.ands = []  # [ Condition ]

    def convert(self):
        self.reset()
        self.comment(f"when condition (line {self.line_num})")
        self.line(f"DREFOP,f,NULL,NULL,{self.obj},{self.val2}")
        if len(self.ands) > 0:
            for and_cond in self.ands:
                self.comment(f"and condition (line {self.line_num})")
                self.append(and_cond.convert())
        return self.get()


class SetDataref(Converter):
    def __init__(self, name, slope, curve, duration, **kwargs):
        Converter.__init__(self, **kwargs)
        self.name = SetDataref.dataref(name)

        if slope not in ["rise", "fall"]:
            logger.warning(f"invalid set command {slope}, must rise or fall")
            return
        self.slope = slope

        if curve not in ["linear", "sine"]:
            logger.warning(f"invalid set command {curve}, must be sine or linear")
            return
        logger.warning(
            "set command: sine variation not used in LST, using linear variation"
        )
        self.curve = "linear"
        self.duration = duration

    def convert(self):
        self.reset()
        self.comment(f"set dataref {self.name} (line {self.line_num})")
        # To reproduce the groundtraffic behavior, we set the value first,
        # then make it change according to the same pattern as GT.
        start = 1.0 if self.slope == "fall" else 0
        self.comment("set start value")
        self.line(f"DREFOP,{self.name},{start},0,NULL,NULL")
        self.comment("make variation, GT values varies between 0 and 1")
        self.line(f"DREFOP,{self.name},{1 - start},{self.duration},NULL,NULL")
        return self.get()

    @staticmethod
    def dataref(s):
        if s.startswith("var"):
            s = "marginal/groundtraffic/" + s
            return s
        if "/" not in s:
            logger.warning(
                f"invalid dataref path {s}, should be in a domain at least (i.e. contain at least one '/' in path like mydomain/{s})"
            )
        return s


class Train(Converter):
    def __init__(self, name: str, **kwargs):
        Converter.__init__(self, **kwargs)
        self.name = name
        self.train_cars = []

    def convert(self):
        self.reset()
        if len(self.train_cars) < 2:
            logger.warning("invalid train")
            return []
        lead_car = self.train_cars[0]
        self.comment(f"train {self.name} (line {self.line_num})")
        self.line(f"TRAIN,{lead_car.obj}")
        for c in self.train_cars[1:]:
            # self.comment(f"converting route train {c} car")
            self.append(c.convert())
        return self.get()


class TrainCar(Converter):
    def __init__(self, lag, offset, heading, obj, **kwargs):
        Converter.__init__(self, **kwargs)
        self.lag = lag
        self.offset = offset
        self.heading = heading
        self.obj = obj
        logger.debug(f"{obj}")

    def convert(self):
        self.reset()
        self.line(f"TRAINCAR,{self.obj},{self.lag}")
        return self.get()


# ###################################
# ROUTE
#
class Route(Converter):
    def __init__(self, speed: float, offset: float, heading: float, obj: str, **kwargs):
        Converter.__init__(self, **kwargs)
        self.speed = speed
        self.offset = offset
        self.heading = heading
        self.reverse = False
        self.obj = obj
        self.sequence = []

    def label(self):
        if isinstance(self.obj, Train):
            return self.obj.name
        return self.obj

    def convert(self):
        # A GT route gets converted into a LST train
        self.reset()
        if isinstance(self.obj, Train):  # whole train
            self.comment(
                f"converting route train {self.obj.name} {'(reverse)' if self.reverse else ''} (line {self.line_num})"
            )
            self.append(self.obj.convert())
            if self.reverse:
                logger.warning(
                    f"conversion of reverse of route train not supported yet"
                )
        else:  # single object
            self.comment(
                f"converting route single object {'(reverse)' if self.reverse else ''} (line {self.line_num})"
            )
            self.line(f"LOOP,{self.obj}")
            if self.reverse:
                logger.warning(
                    f"conversion of reverse of route object not supported yet"
                )
        for obj in self.sequence:
            cmd = str(obj[0]).lower()
            if cmd == "wp":
                self.line(f"WP,{obj[1][0]},{obj[1][1]},{self.speed}")
                self.ls_points.append([obj[1][1], obj[1][0]])
            elif cmd == "pause":
                self.line(f"WAIT,{obj[1]}")
                if "set" in obj:
                    cmd = str(obj[0]).lower()
                    if cmd != "set":
                        logger.warning(f"not a set command {' '.join(obj)}")
                    elif len(obj) < 5:
                        logger.warning(
                            f"invalid set command {' '.join(obj)}, not enough parameters"
                        )
                    else:
                        set_cmd = SetDataref(
                            name=obj[1], slope=obj[2], curve=obj[3], duration=obj[4]
                        )
                        self.append(set_cmd.convert())
            elif cmd == "backup":
                self.line(f"REVERSE")  # not sure, GT does not rotate the vehicle 180
            elif cmd == "set":
                self.append(obj[1].convert())
            elif cmd in "when":
                self.append(obj[1].convert())
            else:
                logger.warning(f"{cmd} command ignored {' '.join(obj)}")
        self.nl()
        return self.get()


# ###################################
# HIGHWAY
#
class Highway(Converter):
    def __init__(self, speed: float, spacing: float, **kwargs):
        Converter.__init__(self, **kwargs)
        self.speed = speed
        self.spacing = spacing
        self.highway_cars = []
        self.waypoints = []

    def label(self):
        if len(self.highway_cars) > 0:
            return self.highway_cars[0].obj
        return "noname"

    def convert(self):
        # LST highway does not support multiple highwaycar,
        # so we make a highway (the same) for each highwaycar,
        # and play a bit on spawn times.
        self.reset()
        lo = 0
        hi = 0
        for c in self.highway_cars:
            lo = hi
            hi = hi + int(c.offset)
            self.comment(f"Highway at line {self.line_num} for highwaycar {c.obj}")
            self.line(f"HIGHWAY,{c.obj},{lo},{hi}")
            for obj in self.waypoints:
                self.line(f"WP,{obj[0]},{obj[1]},{self.speed}")
                self.ls_points.append([obj[1], obj[0]])
            self.nl()
        return self.get()


class HighwayCar(Converter):
    def __init__(self, offset, heading, obj, **kwargs):
        Converter.__init__(self, **kwargs)
        self.offset = offset
        self.heading = heading
        self.obj = obj


# ###################################
# CONVERTER
#
# By convention, GT keywords are lowercase, LST keywords are UPPERCASE.
#
#
class GroundTraffic(Converter):
    # Parses groundtraffic.txt file and builds a list of "lines"
    # Each line is an a groundtraffic "object" to convert.
    #
    def __init__(self, fn: str, **kwargs):
        Converter.__init__(self, **kwargs)

        self.objects = BigLib(XPLANE_ROOT_PATH)
        self.check_objects = kwargs.get("check_objects", False)
        self.replace_missing = kwargs.get("replace", False)
        self.replacee = kwargs.get("replacee", DEFAULT_OBJECT)
        self.box_buffer = kwargs.get("bbox_buffer", 0.010)
        self.bbox_rounding = kwargs.get("bbox_rounding", 10000)

        self.water = False
        self.debug = False
        self.filename = fn
        self.input_lines = []

        self.commands = []

        self.routes = []
        self.trains = {}
        self.highways = []
        self.datarefs = {}

        self.north = -90
        self.south = 90
        self.east = -180
        self.west = 180

        self.features = []

        self.init()

    def init(self):
        if self.replace_missing and self.replacee is not None:
            self.check_objects(self.replacee)
        self.load()
        logger.debug(f"{__NAME__} rel. {__version__} {__COPYRIGHT__}")

    def check_object(self, name):
        return self.objects.check(name)

    def load(self):
        # Loadss and parses GroundTraffic.txt file.
        # Remember current path for local objects lookup.
        self.input_lines = []

        def get_line(file_pointer):
            line = file_pointer.readline()
            if line == "":
                return None
            line = line.strip()
            self.input_lines.append(line)
            if line.startswith("#"):
                self.commands.append(line)
                logger.debug(line)
                return get_line(file_pointer)
            return line

        if not os.path.exists(self.filename):
            logger.warning(f"file {self.filename} not found")
            return

        localpath, basename = os.path.split(os.path.abspath(self.filename))
        self.objects.set_local_path(localpath)
        fp = open(self.filename, "r", encoding="utf-8", errors="ignore")
        line = get_line(fp)

        current_command = None
        while line is not None:
            line_num = len(self.input_lines)
            args = line.replace("\t", " ").split(" ")
            args[0] = str(args[0]).lower()

            if line.startswith("water"):
                self.water = True
                logger.debug(f"water enabled")
                logger.warning("water command in GT has no equivalent in LST, ignoring")
                line = get_line(fp)
                continue

            elif line.startswith("debug"):
                self.debug = True
                logger.debug(f"debug enabled")
                line = get_line(fp)
                continue

            elif line.startswith("train"):
                args = line.split()
                name = " ".join(args[1:])
                last_train = Train(name=name, line_num=line_num)
                self.trains[name] = last_train
                # waypoints
                line = get_line(fp)

                while line is not None and line != "":
                    args = line.split()
                    if len(args) < 4:
                        logger.warning(
                            f"invalid train car line '{line}', missing arguments?, ignoring"
                        )
                        continue
                    name = " ".join(args[3:])
                    self.check_object(name)
                    last_train.train_cars.append(
                        TrainCar(
                            lag=args[0],
                            offset=args[1],
                            heading=args[2],
                            obj=name,
                            line_num=line_num,
                        )
                    )  # obj=name
                    line = get_line(fp)

                logger.debug(f"created train @{line_num} {len(last_train.train_cars)}")
                last_train = None
                continue

            elif line.startswith("route"):
                last_cond = None
                args = line.split()  # args[0] is keyword route
                if len(args) < 4:
                    logger.warning(
                        f"invalid route line '{line}', missing arguments?, ignoring"
                    )
                    continue
                name = " ".join(args[4:])
                last_route = Route(
                    speed=args[1],
                    offset=args[2],
                    heading=args[3],
                    obj=name,
                    line_num=line_num,
                )  # obj=name
                if self.is_train(name):
                    last_route.obj = self.trains[name]
                else:
                    self.check_object(name)
                self.routes.append(last_route)
                # waypoints
                line = get_line(fp)

                while line is not None and line != "":
                    args = line.split()
                    if args[0] == "pause":
                        # A pause command can have a set associated with it, we split them
                        if len(args) == 2:  # just pause
                            last_route.sequence.append(("pause", args[1]))
                        elif len(args) == 7:  # pause and set
                            last_route.sequence.append(("pause", args[1]))
                            if args[2] == "set":
                                set_cmd = SetDataref(
                                    name=args[3],
                                    slope=args[4],
                                    curve=args[5],
                                    duration=args[6],
                                )
                                last_route.sequence.append(("set", set_cmd))
                            else:
                                logger.warning(
                                    f"got pause command with invalid command '{line}'"
                                )
                        else:
                            logger.warning(
                                f"got pause command with invalid count of arguments '{line}'"
                            )
                    elif args[0] == "at":
                        last_route.sequence.append(("at", " ".join(args[1:])))
                    elif args[0] == "set":
                        if len(args) < 5:
                            logger.warning(
                                f"invalid set command {' '.join(args)}, not enough parameters"
                            )
                            return
                        dref = SetDataref(
                            name=args[1],
                            slope=args[2],
                            curve=args[3],
                            duration=args[4],
                            line_num=line_num,
                        )
                        last_route.sequence.append(("set", dref))
                        self.datarefs[SetDataref.dataref(args[1])] = 1
                    elif args[0] == "when":
                        last_cond = Condition(
                            obj=args[1], val1=args[2], val2=args[3], line_num=line_num
                        )
                        last_route.sequence.append(("when", last_cond))
                    elif args[0] == "and":
                        if last_cond is None:
                            logger.warning(
                                f"got and clause with no pending condition, ignoring and clause"
                            )
                        else:
                            and_cond = Condition(
                                obj=args[1],
                                val1=args[2],
                                val2=args[3],
                                line_num=line_num,
                            )
                            last_cond.ands.append(
                                and_cond
                            )  # not added to sequence, but to last when condition
                    elif args[0] == "backup":
                        last_route.sequence.append(("backup", None))
                    elif args[0] == "reverse":
                        last_route.reverse = True
                        # last_route.sequence.append(("reverse"))
                    else:
                        fargs = [float(f) for f in args]
                        self.bb(*fargs)
                        last_route.sequence.append(("wp", fargs))

                    if last_cond is not None and args[0] not in ["when", "and"]:
                        last_cond = None

                    line = get_line(fp)

                current_command = last_route
                logger.debug(f"created route @{line_num} {len(last_route.sequence)}")
                last_route = None

            elif line.startswith("highway"):
                args = line.split()  # args[0] is highway route
                if len(args) < 2:
                    logger.warning(
                        f"invalid highway line '{line}', missing arguments?, ignoring"
                    )
                    continue
                last_highway = Highway(
                    speed=args[1], spacing=args[2], line_num=line_num
                )
                self.highways.append(last_highway)
                # wagon or waypoints ?
                line = get_line(fp)
                add_wagon = True
                while line is not None and line != "":
                    args = line.split()
                    if add_wagon and len(args) >= 3:  # must assume highway wagon...
                        name = " ".join(args[2:])
                        last_highway.highway_cars.append(
                            HighwayCar(
                                offset=args[0],
                                heading=args[1],
                                obj=name,
                                line_num=line_num,
                            )
                        )  # obj=name
                        self.check_object(name)
                    else:
                        add_wagon = False  # once we don't have 3 values, we assume we get waypoints, we cannot get more wagon
                        if len(args) != 2:
                            logger.warning(
                                f"invalid highway waypoint line '{line}', missing arguments?, ignoring"
                            )
                        else:
                            points = [float(f) for f in args]
                            last_highway.waypoints.append(points)
                            self.bb(*points)
                    line = get_line(fp)
                logger.debug(
                    f"created highway @{line_num} {len(last_highway.highway_cars)} {len(last_highway.waypoints)}"
                )
                current_command = last_highway
                last_highway = None

            elif line != "":
                logger.warning(f"unprocessed GT command '{line}', ignoring")
                continue

            if current_command is not None:
                self.commands.append(current_command)
                logger.debug(
                    f"added command {type(current_command).__name__}: {current_command}"
                )
                current_command = None

            line = get_line(fp)

        fp.close()
        logger.debug(f"{self.filename} {len(self.input_lines)} lines")

    def is_train(self, name) -> bool:
        return name in self.trains.keys()

    def bb(self, lat, lon):
        if lat > self.north:
            self.north = lat
        if lat < self.south:
            self.south = lat
        if lon > self.east:
            self.east = lon
        if lon < self.west:
            self.west = lon

    def bounding_box(self):
        logger.debug(f"{(self.north, self.south, self.east, self.west)}")
        n = self.north
        s = self.south
        if s > n:
            t = s
            s = n
            n = t
        n = min(
            int((n + self.box_buffer) * self.bbox_rounding) / self.bbox_rounding, 90
        )
        s = max(
            int((s - self.box_buffer) * self.bbox_rounding) / self.bbox_rounding, -90
        )
        e = self.east
        w = self.west
        if e < w:
            t = w
            w = e
            e = t
        e = min(
            int((e + self.box_buffer) * self.bbox_rounding) / self.bbox_rounding, 180
        )
        w = max(
            int((w - self.box_buffer) * self.bbox_rounding) / self.bbox_rounding, -180
        )
        logger.debug(f"{(n, s, e, w)}")
        return (n, s, e, w)

    def print(self):
        SEPL = 80
        print("=" * SEPL)
        self.mkinit()
        print("\n".join(self.out))
        print("-" * SEPL)
        self.mkobjects()
        print("\n".join(self.out))
        # print("-" * SEPL)
        # print(json.dumps({
        #     "type": "FeatureCollection",
        #     "features": self.features
        # }, indent=2))
        print("=" * SEPL)

    def save(self, root=None):
        if root is None:
            fn = self.filename.replace(".txt", "").replace(".TXT", "")
            args = os.path.split(fn)
            root = "-" + args[1]

        self.mkinit()
        with open(os.path.join(args[0], "init" + root + ".lst"), "w") as fp:
            fp.write("\n".join(self.out) + "\n")
        logger.info(f"{'init'+root+'.lst'} created")

        self.mkobjects()
        with open(os.path.join(args[0], "objects" + root + ".lst"), "w") as fp:
            fp.write("\n".join(self.out) + "\n")
        logger.info(f"{'objects'+root+'.lst'} created")

        with open(os.path.join(args[0], "paths" + root + ".geojson"), "w") as fp:
            fp.write(
                json.dumps(
                    {"type": "FeatureCollection", "features": self.features}, indent=2
                )
            )
        logger.info(f"{'paths'+root+'.geojson'} created")

        if len(self.datarefs) > 0:
            self.mkdatarefs()
            with open(os.path.join(args[0], "datarefs" + root + ".lst"), "w") as fp:
                fp.write("\n".join(self.out) + "\n")
            logger.info(f"{'datarefs'+root+'.lst'} created")

    def mkinit(self):
        self.reset()
        self.comment(
            f"converted with {__NAME__} rel. {__version__} from {self.filename} on {datetime.now().isoformat()}"
        )
        # Debug flag
        # self.line("1" if self.debug else "0")
        self.line("1")  # force debug during development
        # Scenery boundaries
        for i in self.bounding_box():
            self.line(str(i))
        # Priming time
        self.line("5")  # #seconds of preprocessing
        # Min version
        self.line("MINVER,1.10")
        # Activation dataref
        self.comment("ACTIVEDREF,xcd/gt2lst/lst_active")

    def mkobjects(self, output_comments: bool = True):
        # Print header info
        self.reset()
        self.comment(
            f"converted with {__NAME__} rel. {__version__} from {self.filename} on {datetime.now().isoformat()}"
        )
        for l in self.commands:
            r = None
            logger.debug(f"doing {type(l).__name__}: {l}")
            if isinstance(l, str):
                if not l.startswith("#") or output_comments:
                    r = [l]
            else:
                r = l.convert()
                if type(l) in [Route, Highway]:
                    self.features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "name": l.label(),
                                "length(km)": round(total_length(l.ls_points), 3),
                                "count": len(l.ls_points),
                            },
                            "geometry": {
                                "type": "LineString",
                                "coordinates": l.ls_points,
                            },
                        }
                    )
            if r is not None and len(r) > 0:
                self.append(r)
        (n, s, e, w) = (self.north, self.south, self.east, self.west)
        self.features.append(
            {
                "type": "Feature",
                "properties": {"name": "bbox"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[w, n], [e, n], [e, s], [w, s], [w, n]]],
                },
            }
        )
        (n, s, e, w) = self.bounding_box()
        self.features.append(
            {
                "type": "Feature",
                "properties": {"name": "bbox with buffer"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[w, n], [e, n], [e, s], [w, s], [w, n]]],
                },
            }
        )

    def mkdatarefs(self):
        self.reset()
        self.comment("dataref initialisation")
        for dref, value in self.datarefs.items():
            self.line(f"DREF,{dref},{value}")

def main():
    args = parser.parse_args()
    fn=args.ground_traffic_file

    if fn is None:
        parser.print_help()
        sys.exit(1)

    gt = GroundTraffic(fn, bbox_buffer=0.001)

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

# ###################################
# CONVERTER
#
if __name__ == "__main__":
    main()