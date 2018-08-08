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
from locale import gettext as _

from gi.repository import Gtk, GdkPixbuf

import pexpect

gtk_version = (Gtk.get_major_version(),
               Gtk.get_minor_version(),
               Gtk.get_micro_version())


def check_gtk_version(major_version, minor_version, micro=0):
    """Return true if running gtk >= requested version"""
    return gtk_version >= (major_version, minor_version, micro)


# Check if the LANG variable needs to be set
use_env = False


def check_dependencies(commands=[]):
    """Check for the existence of required commands, and sudo access"""
    # Check for sudo
    if pexpect.which("sudo") is None:
        return False

    # Check for required commands
    for command in commands:
        if pexpect.which(command) is None:
            return False

    # Check for LANG requirements
    child = None
    try:
        child = env_spawn('sudo', ['-v'], 1)
        if child.expect([".*ssword.*", "Sorry",
                         pexpect.EOF,
                         pexpect.TIMEOUT]) == 3:
            global use_env
            use_env = True
        child.close()
    except OSError:
        if child is not None:
            child.close()
        return False

    # Check for sudo rights
    child = env_spawn('sudo', ['-v'], 1)
    try:
        index = child.expect([".*ssword.*", "Sorry",
                              pexpect.EOF, pexpect.TIMEOUT])
        child.close()
        if index == 0 or index == 2:
            # User in sudoers, or already admin
            return True
        elif index == 1 or index == 3:
            # User not in sudoers
            return False

    except:
        # Something else went wrong.
        child.close()

    return False


def env_spawn(command, args, timeout):
    """Use pexpect.spawn, adapt for timeout and env requirements."""
    env = os.environ
    env["LANG"] = "C"
    if use_env:
        child = pexpect.spawn(command, args, env)
    else:
        child = pexpect.spawn(command, args)
    child.timeout = timeout
    return child


class SudoDialog(Gtk.Dialog):

    '''
    Creates a new SudoDialog. This is a replacement for using gksudo which
    provides additional flexibility when performing sudo commands.

    Only used to verify password by issuing 'sudo /bin/true'.

    Keyword arguments:
    - parent:   Optional parent Gtk.Window
    - icon:     Optional icon name or path to image file.
    - message:  Optional message to be displayed instead of the defaults.
    - name:     Optional name to be displayed, for when message is not used.
    - retries:  Optional maximum number of password attempts. -1 is unlimited.

    Signals emitted by run():
    - NONE:     Dialog closed.
    - CANCEL:   Dialog cancelled.
    - REJECT:   Password invalid.
    - ACCEPT:   Password valid.
    '''

    def __init__(self, title=None, parent=None, icon=None, message=None,
                 name=None, retries=-1):
        """Initialize the SudoDialog."""
        # initialize the dialog
        super(SudoDialog, self).__init__(title=title,
                                         transient_for=parent,
                                         modal=True,
                                         destroy_with_parent=True)
        #
        self.connect("show", self.on_show)
        if title is None:
            title = _("Password Required")
        self.set_title(title)

        self.set_border_width(5)

        # Content Area
        content_area = self.get_content_area()
        grid = Gtk.Grid.new()
        grid.set_row_spacing(6)
        grid.set_column_spacing(12)
        grid.set_margin_left(5)
        grid.set_margin_right(5)
        content_area.add(grid)

        # Icon
        self.dialog_icon = Gtk.Image.new_from_icon_name("dialog-password",
                                                        Gtk.IconSize.DIALOG)
        grid.attach(self.dialog_icon, 0, 0, 1, 2)

        # Text
        self.primary_text = Gtk.Label.new("")
        self.primary_text.set_use_markup(True)
        self.primary_text.set_halign(Gtk.Align.START)
        self.secondary_text = Gtk.Label.new("")
        self.secondary_text.set_use_markup(True)
        self.secondary_text.set_halign(Gtk.Align.START)
        self.secondary_text.set_margin_top(6)
        grid.attach(self.primary_text, 1, 0, 1, 1)
        grid.attach(self.secondary_text, 1, 1, 1, 1)

        # Infobar
        self.infobar = Gtk.InfoBar.new()
        self.infobar.set_margin_top(12)
        self.infobar.set_message_type(Gtk.MessageType.WARNING)
        content_area = self.infobar.get_content_area()
        infobar_icon = Gtk.Image.new_from_icon_name("dialog-warning",
                                                    Gtk.IconSize.BUTTON)
        label = Gtk.Label.new(_("Incorrect password... try again."))
        content_area.add(infobar_icon)
        content_area.add(label)
        grid.attach(self.infobar, 0, 2, 2, 1)
        content_area.show_all()
        self.infobar.set_no_show_all(True)

        # Password
        label = Gtk.Label.new("")
        label.set_use_markup(True)
        label.set_markup("<b>%s</b>" % _("Password:"))
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(12)
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        self.password_entry.set_margin_top(12)
        grid.attach(label, 0, 3, 1, 1)
        grid.attach(self.password_entry, 1, 3, 1, 1)

        # Buttons
        button = self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        button_box = button.get_parent()
        button_box.set_margin_top(24)
        ok_button = Gtk.Button.new_with_label(_("OK"))
        ok_button.connect("clicked", self.on_ok_clicked)
        ok_button.set_receives_default(True)
        ok_button.set_can_default(True)
        ok_button.set_sensitive(False)
        self.set_default(ok_button)
        if check_gtk_version(3, 12):
            button_box.pack_start(ok_button, True, True, 0)
        else:
            button_box.pack_start(ok_button, False, False, 0)

        self.password_entry.connect("changed", self.on_password_changed,
                                    ok_button)

        self.set_dialog_icon(icon)

        # add primary and secondary text
        if message:
            primary_text = message
            secondary_text = None
        else:
            primary_text = _("Enter your password to\n"
                             "perform administrative tasks.")
            secondary_text = _("The application '%s' lets you\n"
                               "modify essential parts of your system." % name)
        self.format_primary_text(primary_text)
        self.format_secondary_text(secondary_text)

        self.attempted_logins = 0
        self.max_attempted_logins = retries

        self.show_all()

    def on_password_changed(self, widget, button):
        """Set the apply button sensitivity based on password input."""
        button.set_sensitive(len(widget.get_text()) > 0)

    def format_primary_text(self, message_format):
        '''
        Format the primary text widget.
        '''
        self.primary_text.set_markup("<big><b>%s</b></big>" % message_format)

    def format_secondary_text(self, message_format):
        '''
        Format the secondary text widget.
        '''
        self.secondary_text.set_markup(message_format)

    def set_dialog_icon(self, icon=None):
        '''
        Set the icon for the dialog. If the icon variable is an absolute
        path, the icon is from an image file. Otherwise, set the icon from an
        icon name.
        '''
        # default icon size is dialog.
        icon_size = Gtk.IconSize.DIALOG
        if icon:
            if os.path.isfile(os.path.abspath(icon)):
                # icon is a filename, so load it into a pixbuf to an image
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon,
                                                                icon_size,
                                                                icon_size)
                self.dialog_icon.set_from_pixbuf(pixbuf)
                self.set_icon_from_file(icon)
            else:
                # icon is an named icon, so load it directly to an image
                self.dialog_icon.set_from_icon_name(icon, icon_size)
                self.set_icon_name(icon)
        else:
            # fallback on password icon
            self.dialog_icon.set_from_icon_name('dialog-password', icon_size)
            self.set_icon_name('dialog-password')

    def on_show(self, widget):
        '''When the dialog is displayed, clear the password.'''
        self.set_password('')
        self.password_valid = False

    def on_ok_clicked(self, widget):
        '''
        When the OK button is clicked, attempt to use sudo with the currently
        entered password.  If successful, emit the response signal with ACCEPT.

        If unsuccessful, try again until reaching maximum attempted logins,
        then emit the response signal with REJECT.
        '''
        if self.attempt_login():
            self.password_valid = True
            self.emit("response", Gtk.ResponseType.ACCEPT)
        else:
            self.password_valid = False
            # Adjust the dialog for attactiveness.
            self.infobar.show()
            self.password_entry.grab_focus()
            if self.attempted_logins == self.max_attempted_logins:
                self.attempted_logins = 0
                self.emit("response", Gtk.ResponseType.REJECT)

    def get_password(self):
        '''Return the currently entered password, or None if blank.'''
        if not self.password_valid:
            return None
        password = self.password_entry.get_text()
        if password == '':
            return None
        return password

    def set_password(self, text=None):
        '''Set the password entry to the defined text.'''
        if text is None:
            text = ''
        self.password_entry.set_text(text)
        self.password_valid = False

    def attempt_login(self):
        '''
        Try to use sudo with the current entered password.

        Return True if successful.
        '''
        # Set the pexpect variables and spawn the process.
        child = env_spawn('sudo', ['/bin/true'], 1)
        try:
            # Check for password prompt or program exit.
            child.expect([".*ssword.*", pexpect.EOF])
            child.sendline(self.password_entry.get_text())
            child.expect(pexpect.EOF)
        except pexpect.TIMEOUT:
            # If we timeout, that means the password was unsuccessful.
            pass
        # Close the child process if it is still open.
        child.close()
        # Exit status 0 means success, anything else is an error.
        if child.exitstatus == 0:
            self.attempted_logins = 0
            return True
        self.attempted_logins += 1
        return False
