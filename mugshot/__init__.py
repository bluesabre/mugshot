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

import argparse
import signal

from locale import gettext as _

from gi.repository import Gtk  # pylint: disable=E0611

from mugshot import MugshotWindow

from mugshot_lib import set_up_logging, get_version, helpers


def parse_options():
    """Support for command line options"""
    parser = argparse.ArgumentParser(description="Mugshot %s" % get_version())
    parser.add_argument(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs mugshot_lib also)"))
    options = parser.parse_args()

    set_up_logging(options)


def main():
    'constructor for your class instances'
    parse_options()

    # Run the application.
    window = MugshotWindow.MugshotWindow()
    window.show()

    # Allow application shutdown with Ctrl-C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()

    # Cleanup temporary files
    helpers.clear_tempfiles()
