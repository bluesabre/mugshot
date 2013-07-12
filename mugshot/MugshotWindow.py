# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from locale import gettext as _

from gi.repository import Gtk # pylint: disable=E0611
import logging
logger = logging.getLogger('mugshot')

from mugshot_lib import Window
from mugshot.AboutMugshotDialog import AboutMugshotDialog
from mugshot.PreferencesMugshotDialog import PreferencesMugshotDialog

# See mugshot_lib.Window.py for more details about how this class works
class MugshotWindow(Window):
    __gtype_name__ = "MugshotWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(MugshotWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutMugshotDialog
        self.PreferencesDialog = PreferencesMugshotDialog

        # Code for other initialization actions should be added here.

