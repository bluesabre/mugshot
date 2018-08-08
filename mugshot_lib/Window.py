#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#   Mugshot - Lightweight user configuration utility
#   Copyright (C) 2013-2018 Sean Davis <smd.seandavis@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranties of
#   MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging

from gi.repository import Gio, Gtk  # pylint: disable=E0611

from . helpers import get_builder, show_uri

logger = logging.getLogger('mugshot_lib')


class Window(Gtk.Window):

    """This class is meant to be subclassed by MugshotWindow. It provides
    common functions and some boilerplate."""
    __gtype_name__ = "Window"

    # To construct a new instance of this method, the following notable
    # methods are called in this order:
    # __new__(cls)
    # __init__(self)
    # finish_initializing(self, builder)
    # __init__(self)
    #
    # For this reason, it's recommended you leave __init__ empty and put
    # your initialization code in finish_initializing

    def __new__(cls):
        """Special static method that's automatically called by Python when
        constructing a new instance of this class.

        Returns a fully instantiated BaseMugshotWindow object.
        """
        builder = get_builder('MugshotWindow')
        new_object = builder.get_object("mugshot_window")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called while initializing this instance in __new__

        finish_initializing should be called after parsing the UI definition
        and creating a MugshotWindow object with it in order to finish
        initializing the start of the new MugshotWindow instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self, True)
        self.CameraDialog = None  # class
        self.camera_dialog = None  # instance

        self.settings = Gio.Settings.new("apps.mugshot")
        self.settings.connect('changed', self.on_preferences_changed)

        self.tmpfile = None

    def on_help_activate(self, widget, data=None):
        """Show the Help documentation when Help is clicked."""
        show_uri(self, "https://wiki.bluesabre.org/doku.php?id=mugshot-docs")

    def on_menu_camera_activate(self, widget, data=None):
        """Display the camera window for mugshot."""
        if self.camera_dialog is not None:
            logger.debug('show existing camera_dialog')
            self.camera_dialog.show()
        elif self.CameraDialog is not None:
            logger.debug('create new camera_dialog')
            self.camera_dialog = self.CameraDialog()  # pylint: disable=E1102
            self.camera_dialog.connect(
                'apply', self.on_camera_dialog_apply)  # pylint: disable=E1101
            self.camera_dialog.show()

    def on_destroy(self, widget, data=None):
        """Called when the MugshotWindow is closed."""
        # Clean up code for saving application state should be added here.
        if self.tmpfile and os.path.isfile(self.tmpfile.name):
            os.remove(self.tmpfile.name)
        Gtk.main_quit()

    def on_preferences_changed(self, settings, key, data=None):
        """Log preference updates."""
        logger.debug('preference changed: %s = %s' %
                     (key, str(settings.get_value(key))))
