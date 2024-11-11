import sys
import os
import glob
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BigLib")

XPLANE_ROOT_PATH = "/Users/pierre/X-Plane 12"


class BigLib:
    """Fast and naive class to collect "all" library objects in X-Plane directory.

    Please tell me if I don't collect some objects.
    This is used in gt2lst to check whether an object exists before spitting it in LST files.
    """
    def __init__(self, home: str):
        self.home = home
        self.objects = {}
        self.localpath = None
        self.init()

    def init(self):
        self.build()

    def set_local_path(self, path):
        self.localpath = path

    def build(self):
        if not os.path.exists(self.home):
            logger.warning(f"X-Plane folder {self.home} not found, no libraries loaded")
            return
        libs = sorted(glob.glob(os.path.join(self.home, "**/library.txt"), recursive=True))
        for lib in libs:
            self.parse_lib(lib)
        logger.info(f"total {len(self.objects)} objects in {len(libs)} libraries")

    def parse_lib(self, libfn):
        ## WHAT IS THE SEPARATOR?? Not in the specs.
        # What about file names with space in their name
        if not os.path.exists(libfn):
            logger.warning(f"libray folder {libfn} not found, no object loaded")
            return
        libpath, libname = os.path.split(libfn)
        count = 0
        errors = 0
        fp = open(libfn, "r")  # , encoding="UTF-8"
        line = fp.readline()
        while line:
            line = line.strip().rstrip("\n\r")
            line = re.sub(r"[\s]+", ' ', line)  # reduces multiple spaces, tabs, etc. to single space
            if re.match("^EXPORT", line, flags=0):
                args = re.split(r"\t| ", line)
                if len(args) > 2:
                    if args[2] != "":
                        curr = self.objects.get(args[1], [])
                        objpath = os.path.join(libpath, args[2])
                        if not os.path.exists(objpath):
                            logger.debug(f"{objpath} not found")
                            errors = errors + 1
                        curr.append((libpath, args[2], libname))
                        self.objects[args[1]] = curr
                        count = count + 1
                    else:
                        logger.debug(f"problem parsing {line}")
            line = fp.readline()
        fp.close()
        logger.debug(f"{libfn}: {count} objects{f', {errors} object files not found' if errors > 0 else ''}")

    def check(self, path, complain: bool = True):
        # return False if no file associated with the library path was found
        files = self.objects.get(path)
        if files is None:
            # May be it is in a local library
            if self.localpath is not None:
                fn = os.path.join(self.localpath, path)
                if os.path.exists(fn):
                    logger.debug(f"object {path} file {fn} found locally")
                    return True
            if complain:
                logger.warning(f"library object {path} not found")
            return False

        cnt = 0
        for file in files:
            if file[1] == "":
                logger.warning(f"empty path {file}, {files}")
                continue
            # if self.localpath is not None:
            #     fn = os.path.join(self.localpath, file[1])
            #     if os.path.exists(fn):
            #         logger.debug(f"object {path} file {fn} found locally")
            #         return True
            fn = os.path.join(file[0], file[1])
            if not os.path.exists(fn):
                logger.debug(f"object {path} file {fn} not found")
                cnt = cnt + 1
            logger.debug(f"object {path} at {fn}")
        if complain and cnt == len(files):
            logger.warning(f"object {path} file(s) not found")
        return cnt != len(files)


# ###################################
# CONVERT
#
if __name__ == '__main__':
    bl = BigLib(XPLANE_ROOT_PATH)

    # To view transformation on terminal, uses:
    bl.build()

    print(bl.check("MisterX_Library/Airport/Aircraft/Airbus_A320_200/Finnair.obj"))
    print(bl.check("opensceneryx/objects/vehicles/commercial/trucks/dhl.obj"))
    print(bl.check("lib/airport/Ramp_Equipment/Luggage_Cart.obj"))
    print(bl.check("objects/Custum/busgr.obj"))
