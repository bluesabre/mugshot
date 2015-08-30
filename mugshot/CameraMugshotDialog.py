#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#   Mugshot - Lightweight user configuration utility
#   Copyright (C) 2013-2014 Sean Davis <smd.seandavis@gmail.com>
#
#   Portions of this file are adapted from web_cam_box,
#   Copyright (C) 2010 Rick Spencer <rick.spencer@canonical.com>
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

from locale import gettext as _

import logging
logger = logging.getLogger('mugshot')

from gi.repository import Gtk, GObject, Gst, GdkPixbuf
from gi.repository import Cheese, Clutter, GtkClutter

import os

from mugshot_lib import helpers
from mugshot_lib.CameraDialog import CameraDialog

Clutter.init(None)
class CameraBox(GtkClutter.Embed):
    __gsignals__ = {
        'photo-saved': (GObject.SIGNAL_RUN_LAST,
                        GObject.TYPE_NONE,
                        (GObject.TYPE_STRING,)),
        'gst-state-changed': (GObject.SIGNAL_RUN_LAST,
                              GObject.TYPE_NONE,
                              (GObject.TYPE_INT,))
    }
    
    def __init__(self, parent):
        GtkClutter.Embed.__init__(self)
        self.state = Gst.State.NULL
        self.parent = parent
        
        self.stage = self.get_stage()
        self.layout_manager = Clutter.BoxLayout()
        
        self.scroll = Clutter.ScrollActor.new()
        self.scroll.set_scroll_mode(Clutter.ScrollMode.HORIZONTALLY)
        
        self.textures_box = Clutter.Actor(layout_manager=self.layout_manager)
        self.textures_box.set_x_align(Clutter.ActorAlign.CENTER)
        
        self.scroll.add_actor(self.textures_box)
        self.stage.add_actor(self.scroll)

        self.video_texture = Clutter.Texture.new()

        self.layout_manager.pack(self.video_texture, expand=True, x_fill=False, y_fill=False, x_align=Clutter.BoxAlignment.CENTER, y_align=Clutter.BoxAlignment.CENTER)

        self.camera = Cheese.Camera.new(self.video_texture, None, 100, 100)
        Cheese.Camera.setup(self.camera, None)
        Cheese.Camera.play(self.camera)
        self.state = Gst.State.PLAYING

        def added(signal, data):
            node = data.get_device_node()
            self.camera.set_device_by_device_node(node)
            self.camera.switch_camera_device()
            
        device_monitor=Cheese.CameraDeviceMonitor.new()
        device_monitor.connect("added", added)
        device_monitor.coldplug()
        
        self.connect("size-allocate", self.on_size_allocate)
        self.camera.connect("photo-taken", self.on_photo_taken)
        self.camera.connect("state-flags-changed", self.on_state_flags_changed)
        
        self._save_filename = ""
        
    def on_state_flags_changed(self, camera, state):
        self.state = state
        self.emit("gst-state-changed", self.state)
        
    def play(self):
        if self.state != Gst.State.PLAYING:
            Cheese.Camera.play(self.camera)
            
    def pause(self):
        if self.state == Gst.State.PLAYING:
            Cheese.Camera.play(self.camera)
        
    def stop(self):
        Cheese.Camera.stop(self.camera)
    
    def on_size_allocate(self, widget, allocation):
        vheight = self.video_texture.get_height()
        vwidth = self.video_texture.get_width()
        if vheight == 0 or vwidth == 0:
            vformat = self.camera.get_current_video_format()
            vheight = vformat.height
            vwidth = vformat.width
            
        height = allocation.height
        mult = vheight / height
        width = round(vwidth / mult,1)
        
        self.video_texture.set_height(height)
        self.video_texture.set_width(width)
        
        point = Clutter.Point()
        point.x = (self.video_texture.get_width() - allocation.width) / 2
        point.y = 0
        
        self.scroll.scroll_to_point(point)
        
    def take_photo(self, target_filename):
        self._save_filename = target_filename
        return self.camera.take_photo_pixbuf()
        
    def on_photo_taken(self, camera, pixbuf):
        # Get the image dimensions.
        height = pixbuf.get_height()
        width = pixbuf.get_width()
        start_x = 0
        start_y = 0

        # Calculate a balanced center.
        if width > height:
            start_x = (width - height) / 2
            width = height
        else:
            start_y = (height - width) / 2
            height = width

        # Create a new cropped pixbuf.
        new_pixbuf = pixbuf.new_subpixbuf(start_x, start_y, width, height)

        # Overwrite the temporary file with our new cropped image.
        new_pixbuf.savev(self._save_filename, "png", [], [])
        
        self.emit("photo-saved", self._save_filename)
        
        
class CameraMugshotDialog(CameraDialog):
    """Camera Capturing Dialog"""
    __gtype_name__ = "CameraMugshotDialog"
    __gsignals__ = {'apply': (GObject.SIGNAL_RUN_LAST,
                              GObject.TYPE_NONE,
                              (GObject.TYPE_STRING,))
    }

    def finish_initializing(self, builder):  # pylint: disable=E1002
        """Set up the camera dialog"""
        super(CameraMugshotDialog, self).finish_initializing(builder)

        # Initialize Gst or nothing will work.
        Gst.init(None)
        
        self.camera = CameraBox(self)
        self.camera.show()
        
        self.camera.connect("gst-state-changed", self.on_camera_state_changed)
        self.camera.connect("photo-saved", self.on_camera_photo_saved)

        # Pack the video widget into the dialog.
        vbox = builder.get_object('camera_box')
        vbox.pack_start(self.camera, True, True, 0)

        # Essential widgets
        self.record_button = builder.get_object('camera_record')
        self.apply_button = builder.get_object('camera_apply')

        # Store the temporary filename to be used.
        self.filename = None

        self.show_all()
        
    def on_camera_state_changed(self, widget, state):
        if state == Gst.State.PLAYING or self.apply_button.get_sensitive():
            self.record_button.set_sensitive(True)
        else:
            self.record_button.set_sensitive(False)
            
    def on_camera_photo_saved(self, widget, filename):
        self.filename = filename
        self.apply_button.set_sensitive(True)
        self.camera.pause()
        
    def play(self):
        self.camera.play()
        
    def pause(self):
        self.camera.pause()
        
    def stop(self):
        self.camera.stop()

    def take_picture(self, filename):
        self.camera.take_photo(filename)

    def on_camera_record_clicked(self, widget):
        """When the camera record/retry button is clicked:
        Record: Pause the video, start the capture, enable apply and retry.
        Retry: Restart the video stream."""
        # Remove any previous temporary file.
        if self.filename and os.path.isfile(self.filename):
            os.remove(self.filename)

        # Retry action.
        if self.apply_button.get_sensitive():
            self.record_button.set_label(Gtk.STOCK_MEDIA_RECORD)
            self.apply_button.set_sensitive(False)
            self.play()

        # Record (Capture) action.
        else:
            # Create a new temporary file.
            self.filename = helpers.new_tempfile('camera')

            # Capture the current image.
            self.take_picture(self.filename)

            # Set the record button to retry, and disable it until the capture
            # finishes.
            self.record_button.set_label(_("Retry"))
            self.record_button.set_sensitive(False)

    def on_camera_apply_clicked(self, widget):
        """When the camera Apply button is clicked, crop the current photo and
        emit a signal to let the main application know there is a new file
        available.  Then close the camera dialog."""
        self.emit("apply", self.filename)
        self.hide()

    def on_camera_cancel_clicked(self, widget):
        """When the Cancel button is clicked, just hide the dialog."""
        self.hide()
        
    def on_camera_mugshot_dialog_destroy(self, widget, data=None):
        """When the application exits, remove the current temporary file and
        stop the gstreamer element."""
        # Clear away the temp file.
        if self.filename and os.path.isfile(self.filename):
            os.remove(self.filename)
        # Clean up the camera before exiting
        self.camera.stop()

    def on_camera_mugshot_dialog_hide(self, widget, data=None):
        """When the dialog is hidden, pause the camera recording."""
        self.pause()

    def on_camera_mugshot_dialog_show(self, widget, data=None):
        """When the dialog is shown, set the record button to record, disable
        the apply button, and start the camera."""
        self.record_button.set_label(Gtk.STOCK_MEDIA_RECORD)
        self.apply_button.set_sensitive(False)
        self.show_all()
        self.play()

    def on_camera_mugshot_dialog_delete_event(self, widget, data=None):
        """Override the dialog delete event to just hide the window."""
        self.hide()
        return True
