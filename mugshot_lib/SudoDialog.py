#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#   Mugshot - Lightweight user configuration utility
#   Copyright (C) 2013-2014 Sean Davis <smd.seandavis@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License version 3, as published
#   by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranties of
#   MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GdkPixbuf
import os

from locale import gettext as _

import pexpect


class SudoDialog(Gtk.MessageDialog):
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
    def __init__(self, parent=None, icon=None, message=None, name=None,
                 retries=-1):
        """Initialize the SudoDialog."""
        # default dialog parameters
        message_type = Gtk.MessageType.QUESTION
        buttons = Gtk.ButtonsType.NONE

        # initialize the dialog
        super(SudoDialog, self).__init__(transient_for=parent,
                                        modal=True,
                                        destroy_with_parent=True,
                                        message_type=message_type,
                                        buttons=buttons,
                                        text='')
        self.set_dialog_icon(icon)
        self.connect("show", self.on_show)

        # add buttons
        button_box = self.get_children()[0].get_children()[1]
        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        ok_button = Gtk.Button.new_with_label(_("OK"))
        ok_button.connect("clicked", self.on_ok_clicked)
        ok_button.set_receives_default(True)
        ok_button.set_can_default(True)
        ok_button.set_sensitive(False)
        self.set_default(ok_button)
        button_box.pack_start(ok_button, False, False, 0)

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

        # Pack the content area with password-related widgets.
        content_area = self.get_content_area()

        # Use an alignment to move align the password widgets with the text.
        self.password_alignment = Gtk.Alignment()
        # Make an educated guess about how for to align.
        left_align = Gtk.icon_size_lookup(Gtk.IconSize.DIALOG)[1] + 16
        self.password_alignment.set_padding(12, 12, left_align, 0)

        # Outer password box for incorrect password label and inner widgets.
        password_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                    spacing=12)
        password_outer.set_orientation(Gtk.Orientation.VERTICAL)
        # Password error label, only displayed when unsuccessful.
        self.password_info = Gtk.Label(label="")
        self.password_info.set_markup("<b>%s</b>" %
                                      _("Incorrect password... try again."))

        # Inner password box for Password: label and password entry.
        password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                    spacing=12)
        password_label = Gtk.Label(label=_("Password:"))
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_activates_default(True)
        self.password_entry.connect("changed", self._on_password_changed,
                                                                    ok_button)

        # Pack all the widgets.
        password_box.pack_start(password_label, False, False, 0)
        password_box.pack_start(self.password_entry, True, True, 0)
        password_outer.pack_start(self.password_info, True, True, 0)
        password_outer.pack_start(password_box, True, True, 0)
        self.password_alignment.add(password_outer)
        content_area.pack_start(self.password_alignment, True, True, 0)
        content_area.show_all()
        self.password_info.set_visible(False)

        self.attempted_logins = 0
        self.max_attempted_logins = retries

    def _on_password_changed(self, widget, button):
        """Set the apply button sensitivity based on password input."""
        button.set_sensitive(len(widget.get_text()) > 0)

    def format_primary_text(self, message_format):
        '''
        Format the primary text widget.

        API extension to match with format_secondary_text.
        '''
        label = self.get_message_area().get_children()[0]
        label.set_text(message_format)

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
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                self.set_icon_from_file(icon)
            else:
                # icon is an named icon, so load it directly to an image
                image = Gtk.Image.new_from_icon_name(icon, icon_size)
                self.set_icon_name(icon)
        else:
            # fallback on password icon
            image = Gtk.Image.new_from_icon_name('dialog-password', icon_size)
            self.set_icon_name('dialog-password')
        # align, show, and set the image.
        image.set_alignment(Gtk.Align.CENTER, Gtk.Align.FILL)
        image.show()
        self.set_image(image)

    def on_show(self, widget):
        '''When the dialog is displayed, clear the password.'''
        self.set_password('')

    def on_ok_clicked(self, widget):
        '''
        When the OK button is clicked, attempt to use sudo with the currently
        entered password.  If successful, emit the response signal with ACCEPT.

        If unsuccessful, try again until reaching maximum attempted logins,
        then emit the response signal with REJECT.
        '''
        top, bottom, left, right = self.password_alignment.get_padding()
        if self.attempt_login():
            self.password_valid = True
            # Adjust the dialog for attactiveness.
            self.password_alignment.set_padding(12, bottom, left, right)
            self.password_info.hide()
            self.emit("response", Gtk.ResponseType.ACCEPT)
        else:
            self.password_valid = False
            # Adjust the dialog for attactiveness.
            self.password_alignment.set_padding(0, bottom, left, right)
            self.password_info.show()
            self.set_password('')
            if self.attempted_logins == self.max_attempted_logins:
                self.attempted_logins = 0
                self.emit("response", Gtk.ResponseType.REJECT)

    def get_password(self):
        '''Return the currently entered password, or None if blank.'''
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
        child = pexpect.spawn('sudo /bin/true')
        child.timeout = 1
        try:
            # Check for password prompt or program exit.
            child.expect([".*ssword.*", pexpect.EOF])
            child.sendline(self.get_password())
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
        else:
            self.attempted_logins += 1
            return False
