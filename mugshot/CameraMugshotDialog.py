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
from gi.repository import GdkX11, GstVideo  # lint:ok
import cairo

import os

from mugshot_lib import helpers
from mugshot_lib.CameraDialog import CameraDialog


def draw_message(widget, message, ctx):
    """Draw a message (including newlines) vertically centered on a cairo
    context."""
    split_msg = message.split('\n')

    # Get the height and width of the drawing area.
    alloc = widget.get_allocation()
    height = alloc.height

    # Make the background black.
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    # Set the font details.
    font_size = 20
    font_color = (255, 255, 255)
    font_name = "Sans"
    row_spacing = 6
    left_spacing = 10

    # Get start position
    message_height = (len(split_msg) * font_size) + len(split_msg) - 15
    current_pos = (height - message_height) / 2

    # Draw the message to the drawing area.
    ctx.set_source_rgb(*font_color)
    ctx.select_font_face(font_name, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(font_size)

    for line in split_msg:
        ctx.move_to(left_spacing, current_pos)
        ctx.show_text(line)
        current_pos = current_pos + font_size + row_spacing


class CameraMugshotDialog(CameraDialog):
    """Camera Capturing Dialog"""
    __gtype_name__ = "CameraMugshotDialog"

    def finish_initializing(self, builder):  # pylint: disable=E1002
        """Set up the camera dialog"""
        super(CameraMugshotDialog, self).finish_initializing(builder)

        # Initialize Gst or nothing will work.
        Gst.init(None)

        # Pack the video widget into the dialog.
        vbox = builder.get_object('camera_box')
        self.video_window = Gtk.DrawingArea()
        self.video_window.connect("realize", self.__on_video_window_realized)
        vbox.pack_start(self.video_window, True, True, 0)
        self.video_window.show()

        # Prepare the camerabin element.
        self.camerabin = Gst.ElementFactory.make("camerabin", "camera-source")
        if self.camerabin:
            bus = self.camerabin.get_bus()
            bus.add_signal_watch()
            bus.enable_sync_message_emission()
            bus.connect("message", self._on_message)
            bus.connect("sync-message::element", self._on_sync_message)
            self.realized = False
            self.draw_handler = self.video_window.connect('draw', self.on_draw)
        # If the camera fails to load, show an error on the screen.
        else:
            devices = []
            for device in os.listdir('/dev/'):
                if device.startswith('video'):
                    devices.append(device)
            logger.error(_('Camera failed to load. Devices: %s') %
                         '; '.join(devices))
            self.draw_handler = self.video_window.connect('draw',
                                                          self.on_failed_draw)
            self.realized = True

        # Essential widgets
        self.record_button = builder.get_object('camera_record')
        self.apply_button = builder.get_object('camera_apply')

        # Store the temporary filename to be used.
        self.filename = None

        self.show_all()

    def on_failed_draw(self, widget, ctx):
        """Display a message that the camera failed to load."""
        # Translators: Please include newlines, as required to fit the message.
        message = _("Sorry, but your camera\nfailed to initialize.")
        draw_message(widget, message, ctx)

    def on_draw(self, widget, ctx):
        """Display a message that the camera is initializing on first draw.
        Afterwards, blank the drawing area to clear the message."""
        # Translators: Please include newlines, as required to fit the message.
        message = _("Please wait while your\ncamera is initialized.")
        draw_message(widget, message, ctx)

        # Redefine on_draw to blank the drawing area next time.
        def on_draw(self, widget, ctx):
            """Redefinition of on_draw to blank the drawing area next time."""
            ctx.set_source_rgb(0, 0, 0)
            ctx.paint()

            # Redefine on_draw once more to do nothing else.
            def on_draw(self, widget, ctx):
                """Redefinition of on_draw no longer do anything."""
                pass

    def play(self):
        """Start the camera streaming and display the output. It is necessary
        to start the camera playing before using most other functions."""
        if not self.realized:
            self._set_video_window_id()
        if not self.realized:
            logger.error(_("Cannot display camera output. "
                         "Ignoring play command"))
        else:
            if self.camerabin:
                self.camerabin.set_state(Gst.State.PLAYING)

    def pause(self):
        """Pause the camera output. It will cause the image to "freeze".
        Use play() to start the camera playing again. Note that calling pause
        before play may cause errors on certain camera."""
        if self.camerabin:
            self.camerabin.set_state(Gst.State.PAUSED)

    def take_picture(self, filename):
        """take_picture - grab a frame from the webcam and save it to
        'filename.

        If play is not called before take_picture,
        an error may occur. If take_picture is called immediately after play,
        the camera may not be fully initialized, and an error may occur.

        Connect to the signal "image-captured" to be alerted when the picture
        is saved."""
        self.camerabin.set_property("location", filename)
        self.camerabin.emit("start-capture")

    def stop(self):
        """Stop the camera streaming and display the output."""
        self.camerabin.set_state(Gst.State.NULL)

    def _on_message(self, bus, message):
        """Internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.

        arguments -
        bus: the bus from which the message was sent, typically self.bux
        message: the message sent"""
        # Ignore if there is no message.
        if message is None:
            return

        # Get the message type.
        t = message.type

        # Initial load, wait until camera is ready before enabling capture.
        if t == Gst.MessageType.ASYNC_DONE:
            self.record_button.set_sensitive(True)

        if t == Gst.MessageType.ELEMENT:
            # Keep the camera working after several pictures are taken.
            if message.get_structure().get_name() == "image-captured":
                self.camerabin.set_state(Gst.Sate.NULL)
                self.camerabin.set_state(Gst.State.PLAYING)
                self.emit("image-captured", self.filename)

            # Enable interface elements once the images are finished saving.
            elif message.get_structure().get_name() == "image-done":
                self.apply_button.set_sensitive(True)
                self.record_button.set_sensitive(True)
                self.pause()

        # Stop the stream if the EOS (end of stream) message is received.
        if t == Gst.MessageType.EOS:
            self.camerabin.set_state(Gst.State.NULL)

        # Capture and report any error received.
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("%s" % err, debug)

    def _on_sync_message(self, bus, message):
        """ _on_sync_message - internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.

        arguments -
        bus: the bus from which the message was sent, typically self.bux
        message: the message sent

        """
        # Ignore empty messages.
        if message.get_structure() is None:
            return
        message_name = message.get_structure().get_name()
        # Embed the gstreamer element into our window.
        if message_name == "prepare-window-handle":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.video_window.get_window()
                                        .get_xid())

    def __on_video_window_realized(self, widget, data=None):
        """Internal signal handler, used to set up the xid for the drawing area
        in a thread safe manner. Do not call directly."""
        self._set_video_window_id()

    def _set_video_window_id(self):
        """Set the window ID only if not previously configured."""
        if not self.realized and self.video_window.get_window() is not None:
            self.video_window.get_window().get_xid()
            self.realized = True

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
        self.center_crop(self.filename)
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
        self.camerabin.set_state(Gst.State.NULL)

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

    def center_crop(self, filename):
        """Crop the specified file to square dimensions."""
        # Load the image into a Pixbuf.
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)

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
        new_pixbuf.savev(filename, "png", [], [])

    def on_camera_mugshot_dialog_delete_event(self, widget, data=None):
        """Override the dialog delete event to just hide the window."""
        self.hide()
        return True

    # Signals used by CameraMugshotDialog:
    # image-captured: emitted when the camera is done capturing an image.
    # apply: emitted when the apply button has been pressed and there is a
    # new file saved for use.
    __gsignals__ = {'image-captured': (GObject.SIGNAL_RUN_LAST,
                                       GObject.TYPE_NONE,
                                       (GObject.TYPE_PYOBJECT,)),
                    'apply': (GObject.SIGNAL_RUN_LAST,
                              GObject.TYPE_NONE,
                              (GObject.TYPE_STRING,))
                    }
