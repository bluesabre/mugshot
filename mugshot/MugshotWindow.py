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
import dbus

from gi.repository import Gtk, Gdk, GdkPixbuf # pylint: disable=E0611
import logging
logger = logging.getLogger('mugshot')

from mugshot_lib import Window
from mugshot.AboutMugshotDialog import AboutMugshotDialog

username = os.getenv('USER')
if not username:
    username = os.getenv('USERNAME')

def which(command):
    '''Use the system command which to get the absolute path for the given
    command.'''
    return subprocess.Popen(['which', command], \
                            stdout=subprocess.PIPE).stdout.read().strip()
                            
def has_running_process(name):
    command = 'ps -ef | grep " %s" | grep -v "grep"  | wc -l' % name
    n = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).stdout.read().strip()
    return int(n) > 0

def detach_cb(menu, widget):
    '''Detach a widget from its attached widget.'''
    menu.detach()
    
def get_entry_value(entry_widget):
    """Get the value from one of the Mugshot entries."""
    # Get the text from an entry, changing none to ''
    value = entry_widget.get_text().strip()
    if value.lower() == 'none':
        value = ''
    return value
    
def menu_position(self, menu, data=None, something_else=None):
    '''Position a menu at the bottom of its attached widget'''
    widget = menu.get_attach_widget()
    allocation = widget.get_allocation()
    window_pos = widget.get_window().get_position()
    # Align the left side of the menu with the left side of the button.
    x = window_pos[0] + allocation.x
    # Align the top of the menu with the bottom of the button.
    y = window_pos[1] + allocation.y + allocation.height
    return (x, y, True)

# See mugshot_lib.Window.py for more details about how this class works
class MugshotWindow(Window):
    __gtype_name__ = "MugshotWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(MugshotWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutMugshotDialog
        
        # User Image widgets
        self.image_button = builder.get_object('image_button')
        self.user_image = builder.get_object('user_image')
        self.image_menu = builder.get_object('image_menu')
        self.image_menu.attach_to_widget(self.image_button, detach_cb)
        
        # Entry widgets (chfn)
        self.first_name_entry = builder.get_object('first_name')
        self.last_name_entry = builder.get_object('last_name')
        self.initials_entry = builder.get_object('initials')
        self.office_phone_entry = builder.get_object('office_phone')
        self.home_phone_entry = builder.get_object('home_phone')
        self.email_entry = builder.get_object('email')
        self.fax_entry = builder.get_object('fax')
        
        # Stock photo browser
        self.stock_browser = builder.get_object('stock_browser')
        self.iconview = builder.get_object('stock_iconview')

        # Populate all of the widgets.
        self.init_user_details()
        
    def init_user_details(self):
        """Initialize the user details entries and variables."""
        # Check for .face and set profile image.
        logger.debug('Checking for ~/.face profile image')
        face = os.path.expanduser('~/.face')
        if os.path.isfile(face):
            self.set_user_image(face)
        else:
            self.set_user_image(None)
        self.updated_image = None
        
        # Search /etc/passwd for the current user's details.
        logger.debug('Getting user details from /etc/passwd')
        for line in open('/etc/passwd', 'r'):
            if line.startswith(username + ':'):
                logger.debug('Found details: %s' % line.strip())
                details = line.split(':')[4]
                name, office, office_phone, home_phone = details.split(',', 3)
                break
                
        # Expand the user's fullname into first, last, and initials.
        try:
            first_name, last_name = name.split(' ', 1)
            initials = first_name[0] + last_name[0]
        except:
            first_name = name
            last_name = ''
            initials = first_name[0]
            
        # If the variables are defined as 'none', use blank for cleanliness.
        if home_phone == 'none': home_phone = ''
        if office_phone == 'none': office_phone = ''
        
        # Get dconf settings
        if self.settings['initials'] != '':
            initials = self.settings['initials']
        email = self.settings['email']
        fax = self.settings['fax']
                    
        # Set the class variables
        self.first_name = first_name
        self.last_name = last_name
        self.initials = initials
        self.home_phone = home_phone
        self.office_phone = office_phone
                    
        # Populate the GtkEntries.
        self.first_name_entry.set_text(self.first_name)
        self.last_name_entry.set_text(self.last_name)
        self.initials_entry.set_text(self.initials)
        self.office_phone_entry.set_text(self.office_phone)
        self.home_phone_entry.set_text(self.home_phone)
        self.email_entry.set_text(email)
        self.fax_entry.set_text(fax)
            
    # = Mugshot Window ======================================================= #
    def set_user_image(self, filename=None):
        """Scale and set the user profile image."""
        logger.debug("Setting user profile image to %s" % str(filename))
        if filename:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            scaled = pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.HYPER)
            self.user_image.set_from_pixbuf(scaled)
        else:
            self.user_image.set_from_icon_name('avatar-default', 128)

    def filter_numbers(self, entry, *args):
        """Allow only numbers and + in phone entry fields."""
        text = entry.get_text().strip()
        entry.set_text(''.join([i for i in text if i in '+0123456789']))
    
    def on_apply_button_clicked(self, widget):
        """When the window Apply button is clicked, commit any relevant 
        changes."""
        if self.get_chfn_details_updated():
            returns = self.save_chfn_details()
            
        if self.get_libreoffice_details_updated():
            self.set_libreoffice_data()
                
        if self.updated_image:
            self.save_image()
            
        self.save_gsettings()
            
    def save_gsettings(self):
        """Save details to dconf (the ones not tracked by /etc/passwd)"""
        self.settings.set_string('initials', get_entry_value(self.initials_entry))
        self.settings.set_string('email', get_entry_value(self.email_entry))
        self.settings.set_string('fax', get_entry_value(self.fax_entry))
            
    def on_cancel_button_clicked(self, widget):
        """When the window cancel button is clicked, close the program."""
        self.destroy()
        
    # = Image Button and Menu ================================================ #
    def on_image_button_clicked(self, widget):
        """When the menu button is clicked, display the appmenu."""
        if widget.get_active():
            self.image_menu.popup(None, None, menu_position, 
                                        self.image_menu, 3, 
                                        Gtk.get_current_event_time())
                                                  
    def on_image_menu_hide(self, widget):
        """Untoggle the image button when the menu is hidden."""
        self.image_button.set_active(False)
        
    def save_image(self):
        """Copy the updated image filename to ~/.face"""
        # Check if the image has been updated.
        if not self.updated_image:
            return False
            
        face = os.path.expanduser('~/.face')
        
        # If the .face file already exists, remove it first.
        if os.path.isfile(face):
            os.remove(face)
            
        # Copy the new file to ~/.face
        shutil.copyfile(self.updated_image, face)
        self.set_pidgin_buddyicon(face)
        self.updated_image = None
        return True
        
    def set_pidgin_buddyicon(self, filename=None):
        """Sets the pidgin buddyicon to filename (usually ~/.face).
        
        If pidgin is running, use the dbus interface, otherwise directly modify
        the XML file."""
        prefs_file = os.path.expanduser('~/.purple/prefs.xml')
        if not os.path.exists(prefs_file):
            return
        if has_running_process('pidgin'):
            self.set_pidgin_buddyicon_dbus(filename)
        else:
            self.set_pidgin_buddyicon_xml(filename)
            
    def set_pidgin_buddyicon_dbus(self, filename=None):
        """Set the pidgin buddy icon via dbus."""
        bus = dbus.SessionBus()
        obj = bus.get_object("im.pidgin.purple.PurpleService", 
                             "/im/pidgin/purple/PurpleObject")
        purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")
        # To make the change instantly visible, set the icon to none first.
        purple.PurplePrefsSetPath('/pidgin/accounts/buddyicon', '')
        if filename:
            purple.PurplePrefsSetPath('/pidgin/accounts/buddyicon', filename)
        
    def set_pidgin_buddyicon_xml(self, filename=None):
        """Set the buddyicon used by pidgin to filename (via the xml file)."""
        # This is hacky, but a working implementation for now...
        prefs_file = os.path.expanduser('~/.purple/prefs.xml')
        tmp_buffer = []
        if os.path.isfile(prefs_file):
            for line in open(prefs_file):
                if '<pref name=\'buddyicon\'' in line:
                    new = line.split('value=')[0] 
                    if filename:
                        new = new + 'value=\'%s\'/>\n' % filename 
                    else:
                        new = new + 'value=\'\'/>\n'
                    tmp_buffer.append(new)
                else:
                    tmp_buffer.append(line)
            write_prefs = open(prefs_file, 'w')
            for line in tmp_buffer:
                write_prefs.write(line)
            write_prefs.close()
        
    # = chfn functions ============================================ #
    def get_chfn_details_updated(self):
        """Return True if chfn-related details have been modified."""
        if self.first_name != self.first_name_entry.get_text().strip() or \
            self.last_name != self.last_name_entry.get_text().strip() or \
            self.home_phone != self.home_phone_entry.get_text().strip() or \
            self.office_phone != self.office_phone_entry.get_text().strip():
            return True
        return False
    
    def save_chfn_details(self):
        """Commit changes to chfn-related details.  For full name, changes must
        be performed as root.  Other changes are done with the user password.
        
        Return exit codes for 1) full name changes and 2) home/work phone
        changes.
        
        e.g. [0, 0] (both passed)"""
        return_codes = []
        
        # Get the user's password
        password = self.get_password()
        if not password:
            return return_codes
            
        username = os.getenv('USER')
        chfn = which('chfn')
            
        # Get each of the updated values.
        first_name = get_entry_value(self.first_name_entry)
        last_name = get_entry_value(self.last_name_entry)
        full_name = "%s %s" % (first_name, last_name)
        full_name = full_name.strip()
        office_phone = get_entry_value(self.office_phone_entry)
        if office_phone == '':
            office_phone = 'none'
        home_phone = get_entry_value(self.home_phone_entry)
        if home_phone == '':
            home_phone = 'none'
        
        # Full name can only be modified by root.  Try using sudo to modify.
        logger.debug('Attempting to set fullname with sudo chfn')
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
            logger.debug('Timeout reached, password was incorrect or sudo ' \
                         'right not granted.')
            pass 
        child.close()
        if child.exitstatus == 0:
            self.first_name = first_name
            self.last_name = last_name
        return_codes.append(child.exitstatus)

        logger.debug('Attempting to set user details with chfn')
        child = pexpect.spawn('chfn')
        child.timeout = 5
        try:
            child.expect(['Password: ', pexpect.EOF])
            child.sendline(password)
            child.expect('Room Number.*:')
            child.sendline('')
            child.expect('Work Phone.*:')
            child.sendline(office_phone)
            child.expect('Home Phone.*:')
            child.sendline(home_phone)
            child.sendline(home_phone)
        except pexpect.TIMEOUT:
            logger.debug('Timeout reached, password was likely incorrect.')
        child.close(True)
        if child.exitstatus == 0:
            self.office_phone = office_phone
            self.home_phone = home_phone
        return_codes.append(child.exitstatus)
        return return_codes
        
    # = LibreOffice ========================================================== #
    def get_libreoffice_details_updated(self):
        """Return True if LibreOffice settings need to be updated."""
        # Return False if there is no preferences file.
        prefs_file = os.path.expanduser('~/.config/libreoffice/4/user/registrymodifications.xcu')
        if not os.path.isfile(prefs_file):
            return False
        # Compare the current entries to the existing LibreOffice data.
        data = self.get_libreoffice_data()
        if data['first_name'] != get_entry_value(self.first_name_entry):
            return True
        if data['last_name'] != get_entry_value(self.last_name_entry):
            return True
        if data['initials'] != get_entry_value(self.initials_entry):
            return True
        if data['email'] != get_entry_value(self.email_entry):
            return True
        if data['home_phone'] != get_entry_value(self.home_phone_entry):
            return True
        if data['office_phone'] != get_entry_value(self.office_phone_entry):
            return True
        if data['fax'] != get_entry_value(self.fax_entry):
            return True
        return False
    
    def get_libreoffice_data(self):
        """Get each of the preferences from the LibreOffice registymodifications
        preferences file.
        
        Return a dict with the details."""
        prefs_file = os.path.expanduser('~/.config/libreoffice/4/user/registrymodifications.xcu')
        data = {'first_name': '', 'last_name': '', 'initials': '', 'email': '', 
                'home_phone': '', 'office_phone': '', 'fax': ''}
        if os.path.isfile(prefs_file):
            for line in open(prefs_file):
                if "UserProfile/Data" in line:
                    value = line.split('<value>')[1].split('</value>')[0].strip()
                    # First Name
                    if 'name="givenname"' in line:
                        data['first_name'] = value
                    # Last Name
                    elif 'name="sn"' in line:
                        data['last_name'] = value
                    # Initials
                    elif 'name="initials"' in line:
                        data['initials'] = value
                    # Email
                    elif 'name="mail"' in line:
                        data['email'] = value
                    # Home Phone
                    elif 'name="homephone"' in line:
                        data['home_phone'] = value
                    # Office Phone
                    elif 'name="telephonenumber"' in line:
                        data['office_phone'] = value
                    # Fax Number
                    elif 'name="facsimiletelephonenumber"' in line:
                        data['fax'] = value
                    else:
                        pass
        return data
        
    def set_libreoffice_data(self):
        """Update the LibreOffice registymodifications preferences file."""
        prefs_file = os.path.expanduser('~/.config/libreoffice/4/user/registrymodifications.xcu')
        if os.path.isfile(prefs_file):
            tmp_buffer = []
            for line in open(prefs_file):
                new = None
                if "UserProfile/Data" in line:
                    new = line.split('<value>')[0]
                    # First Name
                    if 'name="givenname"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.first_name_entry)
                    # Last Name
                    elif 'name="sn"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.last_name_entry)
                    # Initials
                    elif 'name="initials"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.initials_entry)
                    # Email
                    elif 'name="mail"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.email_entry)
                    # Home Phone
                    elif 'name="homephone"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.home_phone_entry)
                    # Office Phone
                    elif 'name="telephonenumber"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.office_phone_entry)
                    # Fax Number
                    elif 'name="facsimiletelephonenumber"' in line:
                        new = new + '<value>%s</value></prop></item>\n' % \
                                    get_entry_value(self.fax_entry)
                    else:
                        new = line
                    tmp_buffer.append(new)
                else:
                    tmp_buffer.append(line)
            open_prefs = open(prefs_file, 'w')
            for line in tmp_buffer:
                open_prefs.write(line)
            open_prefs.close()
                    
    # = Stock Browser ======================================================== #
    def on_image_from_stock_activate(self, widget):
        """When the 'Select image from stock' menu item is clicked, load and 
        display the stock photo browser."""
        self.load_stock_browser()
        self.stock_browser.show_all()
        
    def load_stock_browser(self):
        """Load the stock photo browser."""
        # Check if the photos have already been loaded.
        model = self.iconview.get_model()
        if len(model) != 0:
            logger.debug("Stock browser already loaded.")
            return
            
        # If they have not, load each photo from /usr/share/pixmaps/faces.
        logger.debug("Loading stock browser photos.")
        for filename in os.listdir('/usr/share/pixmaps/faces'):
            full_path = os.path.join('/usr/share/pixmaps/faces/', filename)
            if os.path.isfile(full_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(full_path)
                scaled = pixbuf.scale_simple(90, 90, GdkPixbuf.InterpType.HYPER)
                model.append([full_path, scaled])
                
    def on_stock_browser_delete_event(self, widget, event):
        """Hide the stock browser instead of deleting it."""
        widget.hide()
        return True
        
    def on_stock_cancel_clicked(self, widget):
        """Hide the stock browser when Cancel is clicked."""
        self.stock_browser.hide()
        
    def on_stock_ok_clicked(self, widget):
        """When the stock browser OK button is clicked, get the currently 
        selected photo and set it to the user profile image."""
        selected_items = self.iconview.get_selected_items()
        if len(selected_items) != 0:
            # Get the filename from the stock browser iconview.
            path = int(selected_items[0].to_string())
            filename = self.iconview.get_model()[path][0]
            logger.debug("Selected %s" % filename)
            
            # Update variables and widgets, then hide.
            self.set_user_image(filename)
            self.updated_image = filename
            self.stock_browser.hide()
            
    def on_stock_iconview_item_activated(self, widget, path):
        self.on_stock_ok_clicked(widget)
        
    # = Image Browser ======================================================== #
    def on_image_from_browse_activate(self, widget):
        """Browse for a user profile image."""
        # Initialize a GtkFileChooserDialog.
        chooser = Gtk.FileChooserDialog(_("Select an image"), self, 
                                    Gtk.FileChooserAction.OPEN, 
                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, 
                                    Gtk.STOCK_OK, Gtk.ResponseType.OK))
                                    
        # Add a filter for only image files.
        image_filter = Gtk.FileFilter()
        image_filter.set_name('Images')
        image_filter.add_mime_type('image/*')
        chooser.add_filter(image_filter)
        
        # Run the dialog, grab the filename if confirmed, then hide the dialog.
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            # Update the user image, store the path for committing later.
            self.updated_image = chooser.get_filename()
            logger.debug("Selected %s" % self.updated_image)
            self.set_user_image(self.updated_image)
        chooser.hide()
        
    # = Password Entry ======================================================= #
    def get_password(self):
        """Display a password dialog for authenticating to sudo and chfn."""
        logger.debug("Prompting user for password")
        dialog = self.builder.get_object('password_dialog')
        entry = self.builder.get_object('password_entry')
        response = dialog.run()
        dialog.hide()
        if response == Gtk.ResponseType.OK:
            logger.debug("Password entered")
            pw = entry.get_text()
            entry.set_text('')
            return pw
        logger.debug("Cancelled")
        return None
        
    def on_password_entry_activate(self, widget):
        """On Password Entry activate, click OK."""
        self.builder.get_object('password_ok').activate()
    
