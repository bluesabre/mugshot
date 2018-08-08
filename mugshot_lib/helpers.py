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

"""Helpers for an Ubuntu application."""
import logging
import os

import tempfile

from . mugshotconfig import get_data_file
from . Builder import Builder


def get_builder(builder_file_name):
    """Return a fully-instantiated Gtk.Builder instance from specified ui
    file

    :param builder_file_name: The name of the builder file, without extension.
        Assumed to be in the 'ui' directory under the data path.
    """
    # Look for the ui file that describes the user interface.
    ui_filename = get_data_file('ui', '%s.ui' % (builder_file_name,))
    if not os.path.exists(ui_filename):
        ui_filename = None

    builder = Builder()
    builder.set_translation_domain('mugshot')
    builder.add_from_file(ui_filename)
    return builder


def get_media_file(media_file_name):
    """Retrieve the filename for the specified file."""
    media_filename = get_data_file('media', '%s' % (media_file_name,))
    if not os.path.exists(media_filename):
        media_filename = None

    return "file:///" + media_filename


class NullHandler(logging.Handler):

    """Handle NULL"""

    def emit(self, record):
        """Do not emit anything."""
        pass


def set_up_logging(opts):
    """Set up the logging formatter."""
    # add a handler to prevent basicConfig
    root = logging.getLogger()
    null_handler = NullHandler()
    root.addHandler(null_handler)

    formatter = logging.Formatter("%(levelname)s:%(name)s:"
                                  " %(funcName)s() '%(message)s'")

    logger = logging.getLogger('mugshot')
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    lib_logger = logging.getLogger('mugshot_lib')
    lib_logger_sh = logging.StreamHandler()
    lib_logger_sh.setFormatter(formatter)
    lib_logger.addHandler(lib_logger_sh)

    # Set the logging level to show debug messages.
    if opts.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug('logging enabled')
        if opts.verbose > 1:
            lib_logger.setLevel(logging.DEBUG)


def show_uri(parent, link):
    """Open the URI."""
    from gi.repository import Gtk  # pylint: disable=E0611
    screen = parent.get_screen()
    Gtk.show_uri(screen, link, Gtk.get_current_event_time())


def alias(alternative_function_name):
    '''see http://www.drdobbs.com/web-development/184406073#l9'''
    def decorator(function):
        '''attach alternative_function_name(s) to function'''
        if not hasattr(function, 'aliases'):
            function.aliases = []
        function.aliases.append(alternative_function_name)
        return function
    return decorator


# = Temporary File Management ============================================ #
temporary_files = {}


def new_tempfile(identifier):
    """Create a new temporary file, register it, and return the filename."""
    remove_tempfile(identifier)
    temporary_file = tempfile.NamedTemporaryFile(delete=False)
    temporary_file.close()
    filename = temporary_file.name
    temporary_files[identifier] = filename
    return filename


def get_tempfile(identifier):
    """Retrieve the specified temporary filename."""
    if identifier in list(temporary_files.keys()):
        return temporary_files[identifier]
    return None


def remove_tempfile(identifier):
    """Remove the specified temporary file from the system."""
    if identifier in list(temporary_files.keys()):
        filename = temporary_files[identifier]
        if os.path.isfile(filename):
            os.remove(filename)
        temporary_files.pop(identifier)


def clear_tempfiles():
    """Remove all temporary files registered to Mugshot."""
    for identifier in list(temporary_files.keys()):
        remove_tempfile(identifier)
