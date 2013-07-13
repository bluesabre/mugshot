# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2013 Sean Davis <smd.seandavis@gmail.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from locale import gettext as _

import os
import pexpect
import shutil
import subprocess

from gi.repository import Gtk, Gdk, GdkPixbuf # pylint: disable=E0611
import logging
logger = logging.getLogger('mugshot')

from mugshot_lib import Window
from mugshot.AboutMugshotDialog import AboutMugshotDialog
from mugshot.PreferencesMugshotDialog import PreferencesMugshotDialog

def which(command):
    '''Use the system command which to get the absolute path for the given
    command.'''
    return subprocess.Popen(['which', command], stdout=subprocess.PIPE).stdout.read().strip()

def detach_cb(menu, widget):
    '''Detach a widget from its attached widget.'''
    menu.detach()
    
def menu_position(self, menu, data=None, something_else=None):
    '''Position a menu at the bottom of its attached widget'''
    widget = menu.get_attach_widget()
    allocation = widget.get_allocation()
    window_pos = widget.get_window().get_position()
    x = window_pos[0] + allocation.x
    y = window_pos[1] + allocation.y + allocation.height
    return (x, y, True)

# See mugshot_lib.Window.py for more details about how this class works
class MugshotWindow(Window):
    __gtype_name__ = "MugshotWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(MugshotWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutMugshotDialog
        self.PreferencesDialog = PreferencesMugshotDialog
        
        self.updated_image = None
        
        self.first_name_entry = builder.get_object('first_name')
        self.last_name_entry = builder.get_object('last_name')
        self.initials_entry = builder.get_object('initials')
        self.office_phone_entry = builder.get_object('office_phone')
        self.home_phone_entry = builder.get_object('home_phone')
        self.user_image = builder.get_object('user_image')
        self.image_button = builder.get_object('image_button')
        self.image_menu = builder.get_object('image_menu')
        self.image_menu.attach_to_widget(self.image_button, detach_cb)
        self.iconview = builder.get_object('stock_iconview')
        self.stock_browser = builder.get_object('stock_browser')
        
        face = os.path.expanduser('~/.face')
        if os.path.isfile(face):
            self.set_user_image(face)
        else:
            self.set_user_image(None)

        # Code for other initialization actions should be added here.
        self.first_name, self.last_name, self.initials, self.office_phone, \
            self.home_phone = self.get_user_details()
        if self.home_phone == 'none': self.home_phone = ''
        if self.office_phone == 'none': self.office_phone = ''
        self.first_name_entry.set_text(self.first_name)
        self.last_name_entry.set_text(self.last_name)
        self.initials_entry.set_text(self.initials)
        self.office_phone_entry.set_text(self.office_phone)
        self.home_phone_entry.set_text(self.home_phone)
        
    def on_image_from_browse_activate(self, widget):
        chooser = Gtk.FileChooserDialog(_("Select an image"), self, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        image_filter = Gtk.FileFilter()
        image_filter.set_name('Images')
        image_filter.add_mime_type('image/*')
        chooser.add_filter(image_filter)
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self.updated_image = chooser.get_filename()
            self.set_user_image(self.updated_image)
        chooser.hide()
        
    def on_stock_browser_delete_event(self, widget, event):
        widget.hide()
        return True
        
    def on_image_from_stock_activate(self, widget):
        self.load_stock_browser()
        self.stock_browser.show_all()
        
    def on_image_button_clicked(self, widget):
        """When the menu button is clicked, display the appmenu."""
        if widget.get_active():
            self.image_menu.popup(None, None, menu_position, 
                                        self.image_menu, 3, 
                                        Gtk.get_current_event_time())
                                        
    def on_cancel_button_clicked(self, widget):
        self.destroy()
                                        
    def on_image_menu_hide(self, widget):
        self.image_button.set_active(False)
        
    def get_finger_details_updated(self):
        if self.first_name != self.first_name_entry.get_text().strip() or \
            self.last_name != self.last_name_entry.get_text().strip() or \
            self.home_phone != self.home_phone_entry.get_text().strip() or \
            self.office_phone != self.office_phone_entry.get_text().strip():
            return True
        return False
        
    def on_apply_button_clicked(self, widget):
        if self.get_finger_details_updated():
            self.save_finger()
        if self.updated_image:
            self.save_image()
        
    def set_user_image(self, filename=None):
        if filename:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            scaled = pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.HYPER)
            self.user_image.set_from_pixbuf(scaled)
        else:
            self.user_image.set_from_icon_name('avatar-default', 128)
            
    def load_stock_browser(self):
        model = self.iconview.get_model()
        if len(model) != 0:
            return
        for filename in os.listdir('/usr/share/pixmaps/faces'):
            full_path = os.path.join('/usr/share/pixmaps/faces/', filename)
            if os.path.isfile(full_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(full_path)
                scaled = pixbuf.scale_simple(90, 90, GdkPixbuf.InterpType.HYPER)
                model.append([full_path, scaled])
                
    def on_stock_cancel_clicked(self, widget):
        self.stock_browser.hide()
        
    def on_stock_ok_clicked(self, widget):
        selected_items = self.iconview.get_selected_items()
        if len(selected_items) != 0:
            path = int(selected_items[0].to_string())
            filename = self.iconview.get_model()[path][0]
            self.set_user_image(filename)
            self.updated_image = filename
            self.stock_browser.hide()
            
        
    def get_user_details(self):
        # Get user finger details from /etc/passwd
        username = os.getenv('USER')
        for line in open('/etc/passwd', 'r'):
            if line.startswith(username + ':'):
                details = line.split(':')[4]
                name, office, office_phone, home_phone = details.split(',', 3)
                try:
                    first_name, last_name = name.split(' ', 1)
                    initials = first_name[0] + last_name[0]
                except:
                    first_name = name
                    last_name = ''
                    initials = first_name[0]
        return first_name, last_name, initials, office_phone, home_phone
        
    def get_password(self):
        # Show a password dialog to get password.
        dialog = self.builder.get_object('password_dialog')
        entry = self.builder.get_object('password_entry')
        response = dialog.run()
        dialog.hide()
        if response == Gtk.ResponseType.OK:
            pw = entry.get_text()
            entry.set_text('')
            return pw
        return None
        
    def get_entry_value(self, entry_widget):
        # Get the text from an entry, changing none to ''
        value = entry_widget.get_text().strip()
        if value.lower() == 'none':
            value = ''
        return value
        
    def save_finger(self):
        return_codes = []
        
        # Get the user's password
        password = self.get_password()
        if not password:
            return return_codes
            
        username = os.getenv('USER')
        chfn = which('chfn')
            
        # Get each of the updated values.
        first_name = self.get_entry_value(self.first_name_entry)
        last_name = self.get_entry_value(self.last_name_entry)
        full_name = "%s %s" % (first_name, last_name)
        full_name = full_name.strip()
        office_phone = self.get_entry_value(self.office_phone_entry)
        if office_phone == '':
            office_phone = 'none'
        home_phone = self.get_entry_value(self.home_phone_entry)
        if home_phone == '':
            home_phone = 'none'
        
        # Full name can only be modified by root.  Try using sudo to modify.
        child = pexpect.spawn('sudo %s %s' % (chfn, username))
        child.timeout = 5
        try:
            child.expect([".*ssword.*", pexpect.EOF])
            child.sendline(password)
            child.expect("Full Name.*:")
            child.sendline(full_name)
            for i in range(5):
                child.sendline('')
        except pexpect.TIMEOUT:
            # Password was incorrect, or sudo rights not granted
            pass 
        child.close()
        return_codes.append(child.exitstatus)

        child = pexpect.spawn('chfn')
        child.expect('Password: ')
        child.sendline(password)
        child.expect('Room Number.*:')
        child.sendline('')
        child.expect('Work Phone.*:')
        child.sendline(office_phone)
        child.expect('Home Phone.*:')
        child.sendline(home_phone)
        child.sendline(home_phone)
        child.close(True)
        return_codes.append(child.exitstatus)
        return return_codes
        
    def save_image(self):
        # Copy the updated image to .face
        if not self.updated_image:
            return False
        face = os.path.expanduser('~/.face')
        if os.path.isfile(face):
            os.remove(face)
        shutil.copyfile(self.updated_image, face)
        self.updated_image = None
        return True
            

