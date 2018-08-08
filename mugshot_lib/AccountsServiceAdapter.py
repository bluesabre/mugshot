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

from gi.repository import Gio, GLib


class MugshotAccountsServiceAdapter:

    _properties = {
        "AutomaticLogin": bool,
        "Locked": bool,
        "AccountType": int,
        "PasswordMode": int,
        "SystemAccount": bool,
        "Email": str,
        "HomeDirectory": str,
        "IconFile": str,
        "Language": str,
        "Location": str,
        "RealName": str,
        "Shell": str,
        "UserName": str,
        "XSession": str,
        "Uid": int,
        "LoginFrequency": int,
        "PasswordHint": str,
        "Domain": str,
        "CredentialLifetime": int
    }

    def __init__(self, username):
        self._set_username(username)
        self._available = False
        try:
            self._get_path()
            self._available = True
        except:
            pass

    def available(self):
        return self._available

    def _set_username(self, username):
        self._username = username

    def _get_username(self):
        return self._username

    def _get_path(self):
        return self._find_user_by_name(self._username)

    def _get_variant(self, vtype, value):
        if vtype == bool:
            variant = "(b)"
        elif vtype == int:
            variant = "(i)"
        elif vtype == str:
            variant = "(s)"
        variant = GLib.Variant(variant, (value,))
        return variant

    def _set_property(self, key, value):
        if key not in list(self._properties.keys()):
            return False

        method = "Set" + key
        variant = self._get_variant(self._properties[key], value)

        try:
            bus = self._get_bus()

            bus.call_sync('org.freedesktop.Accounts',
                          self._get_path(),
                          'org.freedesktop.Accounts.User',
                          method, variant,
                          GLib.VariantType.new('()'),
                          Gio.DBusCallFlags.NONE,
                          -1, None)
            return True
        except:
            return False

    def _get_all(self, ):
        try:
            bus = self._get_bus()

            variant = GLib.Variant('(s)',
                                   ('org.freedesktop.Accounts.User',))
            result = bus.call_sync('org.freedesktop.Accounts',
                                   self._get_path(),
                                   'org.freedesktop.DBus.Properties',
                                   'GetAll',
                                   variant,
                                   GLib.VariantType.new('(a{sv})'),
                                   Gio.DBusCallFlags.NONE,
                                   -1,
                                   None)
            (props,) = result.unpack()
            return props
        except:
            return None

    def _get_property(self, key):
        if key not in list(self._properties.keys()):
            return False
        props = self._get_all()
        if props is not None:
            return props[key]
        return False

    def _get_bus(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            return bus
        except:
            return None

    def _find_user_by_name(self, username):
        try:
            bus = self._get_bus()
            result = bus.call_sync('org.freedesktop.Accounts',
                                   '/org/freedesktop/Accounts',
                                   'org.freedesktop.Accounts',
                                   'FindUserByName',
                                   GLib.Variant('(s)', (username,)),
                                   GLib.VariantType.new('(o)'),
                                   Gio.DBusCallFlags.NONE,
                                   -1,
                                   None)
            (path,) = result.unpack()
            return path
        except:
            return None

    def get_email(self):
        return self._get_property("Email")

    def set_email(self, email):
        self._set_property("Email", email)

    def get_location(self):
        return self._get_property("Location")

    def set_location(self, location):
        self._set_property("Location", location)

    def get_icon_file(self):
        """Get user profile image using AccountsService."""
        return self._get_property("IconFile")

    def set_icon_file(self, filename):
        """Set user profile image using AccountsService."""
        self._set_property("IconFile", filename)

    def get_real_name(self):
        return self._get_property("RealName")

    def set_real_name(self, name):
        """Set user profile image using AccountsService."""
        self._set_property("RealName", name)
