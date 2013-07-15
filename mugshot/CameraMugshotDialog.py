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

import logging
logger = logging.getLogger('mugshot')

from gi.repository import Gtk, GdkX11, GObject, Gst, GstVideo

from mugshot_lib.CameraDialog import CameraDialog

class CameraMugshotDialog(CameraDialog):
    __gtype_name__ = "CameraMugshotDialog"

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(CameraMugshotDialog, self).finish_initializing(builder)
        
        Gst.init(None)

        # Code for other initialization actions should be added here.
        vbox = builder.get_object('camera_box')
        self.video_window = Gtk.DrawingArea()
        self.video_window.connect("realize",self.__on_video_window_realized)
        vbox.pack_start(self.video_window, True, True, 0)
        self.video_window.show()
        
        self.camerabin = Gst.ElementFactory.make("camerabin", "camera-source")
        bus = self.camerabin.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self._on_message)
        bus.connect("sync-message::element", self._on_sync_message)
        self.realized = False
        self.show_all()
        ##self.play()
        
    def play(self):
        """play - Start the camera streaming and display the output. It is
        necessary to start the camera playing before using most other functions.
    
        This function has no arguments
        
        """

        if not self.realized:
            self._set_video_window_id()
        if not self.realized:
            print _("Cannot display web cam output. Ignoring play command")
        else:
            self.camerabin.set_state(Gst.State.PLAYING)

    def pause(self):
        """pause - Pause the camera output. It will cause the image to
        "freeze". Use play() to start the camera playng again. Note that
        calling pause before play may cause errors on certain camera.
    
        This function has no arguments
        
        """

        self.camerabin.set_state(Gst.State.PAUSED)

    def take_picture(self, filename):
        """take_picture - grab a frame from the web cam and save it to
        ~/Pictures/datestamp.png, where datestamp is the current datestamp.
        It's possible to add a prefix to the datestamp by setting the
        filename_prefix property. 

        If play is not called before take_picture,
        an error may occur. If take_picture is called immediately after play,
        the camera may not be fully initialized, and an error may occur.        
    
        Connect to the signal "image-captured" to be alerted when the picture
        is saved.

        This function has no arguments

        returns - a string of the filename used to save the image
        
        """
        self.camerabin.set_property("location", filename)
        self.camerabin.emit("start-capture")
        return filename

    def stop(self):
        """stop - Stop the camera streaming and display the output.
    
        This function has no arguments
        
        """

        self.camerabin.set_state(Gst.State.NULL)

    def _on_message(self, bus, message):
        """ _on_message - internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.


        arguments -
        bus: the bus from which the message was sent, typically self.bux
        message: the message sent

        """

        if message is None:
            return

        t = message.type
        #if t == Gst.MessageType.ASYNC_DONE:
        #    print 'finally'
        if t == Gst.MessageType.ELEMENT:
            if message.get_structure().get_name() == "image-captured":
                #work around to keep the camera working after lots
                #of pictures are taken
                self.camerabin.set_state(Gst.Sate.NULL)
                self.camerabin.set_state(Gst.State.PLAYING)

                self.emit("image-captured", self.filename)

        if t == Gst.MessageType.EOS:
            self.camerabin.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug

    def _on_sync_message(self, bus, message):
        """ _on_sync_message - internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.


        arguments -
        bus: the bus from which the message was sent, typically self.bux
        message: the message sent

        """

        if message.get_structure() is None:
            return
        message_name = message.get_structure().get_name()
        if message_name == "prepare-window-handle":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.video_window.get_window().get_xid())

    def __on_video_window_realized(self, widget, data=None):
        """__on_video_window_realized - internal signal handler, used
        to set up the xid for the drawing area in thread safe manner.
        Do not call directly.

        """
        self._set_video_window_id()

    def _set_video_window_id(self):
        if not self.realized and self.video_window.get_window() is not None:
            x = self.video_window.get_window().get_xid()
            self.realized = True

    def on_camera_mugshot_dialog_destroy(self, widget, data=None):
        #clean up the camera before exiting
        self.camerabin.set_state(Gst.State.NULL)
    
    def on_camera_mugshot_dialog_hide(self, widget, data=None):
        self.pause()
        
    def on_camera_mugshot_dialog_show(self, widget, data=None):
        self.show_all()
        self.play()
        
    def on_camera_mugshot_dialog_delete_event(self, widget, data=None):
        self.hide()
        return True
        
    __gsignals__ = {'image-captured' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
		(GObject.TYPE_PYOBJECT,)),
		} 

