# This is a XPPython3 plugin to stop/start LST plugin to provoke
# a config file reload.
#
import os
import xp
from traceback import print_exc

RELEASE = "1.0.1"  # local version number

# Changelog:
#
# 12-SEP-2023: 1.0.1 - Localized path to x-codrdesigns.livingscenerytech domain
# 08-SEP-2023: 1.0.0 - Initial creation
#
LST_RESET_COMMAND = "codrdesigns/livingscenerytech/lst_reset"
LST_RESET_COMMAND_DESC = "Stop and restart LST to provoke config file re-loading"
LST_PLUGIN_SIGNATURE = "com.x-codrdesigns.livingscenerytech"

class PythonInterface:

    def __init__(self):
        self.Name = "Reset LST"
        self.Sig = "xppython3.x-codrdesigns.livingscenerytech.lst_reset"
        self.Desc = f"Stop and restart LST to re-load config files. (Rel. {RELEASE})"
        self.Info = self.Name + f" (rel. {RELEASE})"
        self.enabled = False
        self.trace = True  # produces extra print/debugging in XPPython3.log for this class
        self.menuIdx = None
        self.lst_plugin = None
        self.resetLstCmdRef = None
        self.isRunningRef = None

    def info(self, text):
        print(self.Info, text)

    def debug(self, text):
        if self.trace:
            self.info(text)

    def XPluginStart(self):
        self.debug("PI::XPluginStart: starting..")

        self.resetLstCmdRef = xp.createCommand(LST_RESET_COMMAND, LST_RESET_COMMAND_DESC)
        xp.registerCommandHandler(self.resetLstCmdRef, self.resetLstCmd, 1, None)
        if self.resetLstCmdRef is not None:
            self.debug("PI::XPluginStart: command registered.")
        else:
            self.debug("PI::XPluginStop: command not registered.")

        self.menuIdx = xp.appendMenuItemWithCommand(xp.findPluginsMenu(), self.Name, self.resetLstCmdRef)
        if self.menuIdx is None or (self.menuIdx is not None and self.menuIdx < 0):
            self.info("PI::XPluginStart: menu not added.")
        else:
            self.debug("PI::XPluginStart: menu added.")

        self.debug("PI::XPluginStart: ..started.")
        return self.Name, self.Sig, self.Desc

    def XPluginStop(self):
        self.debug("PI::XPluginStop: stopping..")

        if self.resetLstCmdRef:
            xp.unregisterCommandHandler(self.resetLstCmdRef,
                                        self.resetLstCmd,
                                        1, None)
            self.resetLstCmdRef = None
            self.debug("PI::XPluginStop: command unregistered.")
        else:
            self.debug("PI::XPluginStop: command not unregistered.")

        if self.menuIdx is not None and self.menuIdx >= 0:
            oldidx = self.menuIdx
            xp.removeMenuItem(xp.findPluginsMenu(), self.menuIdx)
            self.menuIdx = None
            self.debug("PI::XPluginStop: menu removed.")
        else:
            self.debug("PI::XPluginStop: menu not removed.")

        return None

    def XPluginEnable(self):
        self.debug("PI::XPluginEnable: enabling..")
        try:
            if self.lst_plugin is not None:
                self.info("PI::XPluginEnable: plugin already found")
            else:
                plugin_id = xp.findPluginBySignature(LST_PLUGIN_SIGNATURE)
                if plugin_id == xp.NO_PLUGIN_ID:
                    self.info(f"PI::XPluginEnable: plugin signature {LST_PLUGIN_SIGNATURE} not found")
                    return 0
                self.lst_plugin = plugin_id
                self.debug(f"PI::XPluginEnable: found {LST_PLUGIN_SIGNATURE} at id {plugin_id}")
            self.enabled = True
            self.debug("PI::XPluginEnable: ..enabled.")
            return 1
        except:
            self.debug("PI::XPluginEnable: ..exception.")
            print_exc()
        return 0

    def XPluginDisable(self):
        self.debug("PI::XPluginDisable: disabling..")
        try:
            self.lst_plugin = None
            self.enabled = False
            self.debug("PI::XPluginDisable: disabled.")
            return None
        except:
            self.debug("PI::XPluginDisable: exception.")
            print_exc()
            self.enabled = False
            return None
        self.enabled = False
        return None

    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass

    def resetLstCmd(self, *args, **kwargs) -> int:
        try:
            if self.enabled:
                self.debug("PI::command executing...")
                if self.lst_plugin is None:
                    self.info("PI::command: no plugin identifier")
                if self.lst_plugin == xp.NO_PLUGIN_ID:
                    self.info("PI::command: invalid plugin identifier (plugin signature not found)")
                if xp.isPluginEnabled(self.lst_plugin):
                    self.debug("lst plugin enabled. disabling..")
                    xp.disablePlugin(self.lst_plugin)
                    self.debug("..disabled. enabling..")
                    xp.enablePlugin(self.lst_plugin)
                    self.debug("..enabled.")
                self.info("LST reset")
                return 0
        except:
            self.debug("PI::command: exception:")
            print_exc()
        return 0  # callback must return 0 or 1.
