# Mugshot
**Mugshot** is a lightweight user configuration utility for Linux designed for simplicity and ease of use. Quickly update your personal profile and sync your updates across applications.

## Features
 - Update your user profile image (~/.face and AccountService)
 - Update user details stored in /etc/passwd (used by *finger* and other desktop applications)
 - (Optionally) sync your profile image to your *Pidgin* buddy icon
 - (Optionally) sync your user details to *LibreOffice*

## Dependencies

### Required
 - chfn
 - python3-cairo
 - python3-dbus
 - python3-gi
 - python3-pexpect

### Optional (for webcam support)
 - gstreamer1.0-plugins-good
 - gstreamer1.0-tools
 - gir1.2-cheese-3.0
 - gir1.2-gtkclutter-1.0

## Installation

### Debian, Ubuntu, and Derivatives
    sudo apt update
    sudo apt install mugshot

### From Source
    sudo python3 setup.py install
    sudo glib-compile-schemas /usr/share/glib-2.0/schemas

### Other Supported Methods
Please submit a bug report or pull request to include additional methods of installation!

## Links
 - [Homepage](https://github.com/bluesabre/mugshot)
 - [Releases](https://github.com/bluesabre/mugshot/releases)
 - [Bug Reports](https://github.com/bluesabre/mugshot/issues)
 - [Translations](https://www.transifex.com/bluesabreorg/mugshot)
 - [Wiki](https://github.com/bluesabre/mugshot/wiki)

## Troubleshooting
If you see the following error:

    (mugshot:22748): GLib-GIO-ERROR **: Settings schema 'apps.mugshot' is not installed

Be sure to copy data/glib-2.0/schemas/apps.mugshot.gschema.xml to either:

 - /usr/share/glib-2.0/schemas, or
 - /usr/local/share/glib-2.0/schemas

and run glib-compile-schemas on that directory before running **Mugshot**.
