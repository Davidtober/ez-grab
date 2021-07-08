"""Main script for the Kivy ezy-grab project


Author: David Tober

30/11/2017
"""
import sys
import os
import string
import json
import threading
import kivy

from functools import partial

from kivy.app import App
from kivy.uix.videoplayer import VideoPlayer
# from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang.builder import Builder
from kivy.properties import DictProperty

from moviepy.editor import VideoFileClip


kivy.require('1.10.0')

ALPHABET = list(string.ascii_lowercase)

class EzyGrab(App):
    """The main app for the ezy-grab project

    Extends:
        App - The default kivy app
    """
    temp_grab_keys = DictProperty()
    settings_container = None
    settings_dir = '.ezygrabrc'

    def __init__(self, video_file=None):
        super(EzyGrab, self).__init__()
        self.button1 = None
        self.button2 = None
        self.timer_func = None

        try:
            settings_file = open(self.settings_dir, 'r+')
        except IOError as err:
            print 'Could not open settings: ', err
            self.grab_keys = {'s': 8, 'm': 16, 'l': 24}
        else:
            self.grab_keys = json.loads(settings_file.read())
            settings_file.close()

        if video_file:
            self.video_file = video_file
            self.open_video(video_file)


    def build(self):
        Window.bind(on_key_down=self.on_key_down)
        # Window.bind(on_motion=self.show_widgets)
        Window.bind(mouse_pos=self.show_widgets)
        widget = Builder.load_file('player.kv')
        self.button1 = widget.children[0]
        self.button2 = widget.children[1]

        # Add the video player underneath all the other elements
        widget.add_widget(self.player, index=5)
        self.timer_func = Clock.schedule_once(self.hide_widgets, 2)
        return widget


    def on_temp_grab_keys(self, instance, value):
        print 'Settings changed'
        if self.settings_container:
            self.settings_container.clear_widgets()
            self.settings_container.add_widget(self.build_settings())
        # Update the settings view in the pop up


    def open_video(self, video_file):
        """Adds specific video file data to the video player and moviepy
        instances

        Arguments:
            video_file {string} -- the path to the video file
        """
        vid_player = VideoPlayer(source=video_file,
                                 state='play',
                                 options={'allow_stretch': True})
        self.clip = VideoFileClip(video_file)
        self.video_file = video_file
        self.player = vid_player

    def on_key_down(self, keyboard, keycode, text, modifiers, *args):
        """[summary]

        Handle the key press event on the video

        Arguments:
            keyboard {[type]} -- [description]
            keycode {[type]} -- [description]
            text {[type]} -- [description]
            modifiers {[type]} -- [description]

        Returns:
            bool -- Return a boolean to stop event propagation
        """
        if keycode == ord(' '):
            # Toggle the player state when space is pressed
            if self.player.state == 'play':
                self.player.state = 'pause'
            else:
                self.player.state = 'play'
            return True

        subclip_length = 0
        for value in self.grab_keys:
            if keycode == ord(value.lower()):
                subclip_length = self.grab_keys[value]
                break

        # Check if grab key set the length or not
        if subclip_length == 0:
            return True

        end = self.player.position
        start = end - subclip_length
        print 'Grabbing from {} to {}'.format(int(start), int(end))
        if start < 0:
            start = 0

        out_file_dir = '{}_grabs'.format(os.path.abspath(self.video_file))
        # Make the output directory if it doesn't exist
        if not os.path.exists(out_file_dir):
            os.makedirs(out_file_dir)
        subclip = self.clip.subclip(start, end)

        # Run the video file maker in it's own thread to not crash the main app
        threading.Thread(target = subclip.write_videofile,
                         args=('{}/{}.mp4'.format(out_file_dir, int(end)), )).start()

        return True

    def hide_widgets(self, *args):
        anim_left = Animation(opacity=0, duration=0.5)
        anim_right = Animation(opacity=0, duration=0.5)
        anim_left.start(self.button1)
        anim_right.start(self.button2)

    def show_widgets(self, *args):
        if self.timer_func:
            # Remove the timer function to hide the widgets if necessary
            Clock.unschedule(self.timer_func)
        self.button1.opacity = 1
        self.button2.opacity = 1
        self.timer_func = Clock.schedule_once(self.hide_widgets, 2)

    def open_new(self):
        App.get_running_app().stop()
        LoadDialog().run()

    def update_settings(self, *_):
        self.grab_keys = self.temp_grab_keys

    def increase_setting(self, key, button):
        self.temp_grab_keys[key] = self.temp_grab_keys[key] + 1
        # button.parent.children[2].text = str(self.temp_grab_keys[key])

    def decrease_setting(self, key, button):
        self.temp_grab_keys[key] = self.temp_grab_keys[key] - 1
        # button.parent.children[2].text = str(self.temp_grab_keys[key])

    def delete_setting(self, key, button):
        del self.temp_grab_keys[key]

    def get_next_letter(self):
        for letter in ALPHABET:
            if letter not in self.temp_grab_keys:
                return letter
        return '-'

    def update_letter(self, old_letter, new_letter, dropdown, element):
        print 'Replacing ', old_letter, ' with ', new_letter, ' on ', element
        self.temp_grab_keys[new_letter] = self.temp_grab_keys[old_letter]
        del self.temp_grab_keys[old_letter]
        element.parent.children[4].text = new_letter
        dropdown.dismiss()

    def build_settings(self):
        settings_layout = GridLayout(cols=1, size_hint=(1, None))
        # Make sure the height is such that there is something to scroll.
        settings_layout.bind(minimum_height=settings_layout.setter('height'))

        for key in self.temp_grab_keys:
            settings_layout.add_widget(self.build_setting(key=key))

        def add_setting(*_):
            next_letter = self.get_next_letter()
            if next_letter != '-':
                self.temp_grab_keys[next_letter] = 10
            # Rebuild the settings layout with the new settings
            # scroll.children[0] = self.build_settings()

        # Add an add new setting button to the layout
        add_button = Button(text='+', height=30, size_hint=(1, None))
        add_button.bind(on_press=add_setting)
        settings_layout.add_widget(add_button)

        return settings_layout

    def build_setting(self, *_, **kwargs):
        if 'key' in kwargs:
            key = kwargs['key']
        else:
            key = self.get_next_letter()
        setting = Builder.load_file('setting.kv')

        dropdown = DropDown()

        # Add the drop-down options to the drop-down
        for letter in ALPHABET:
            if letter not in self.temp_grab_keys:
                btn = Button(text=letter, size_hint_y=None, height=44)
                btn.bind(on_press=partial(self.update_letter, key, letter, dropdown))
                dropdown.add_widget(btn)

        setting.children[5].bind(on_press=dropdown.open)
        setting.children[5].text = key

        if key in self.temp_grab_keys:
            setting.children[3].text = str(self.temp_grab_keys[key])
        else:
            self.temp_grab_keys[key] = 10
            setting.children[3].text = '10'
        print self.temp_grab_keys
        setting.children[4].bind(on_press=partial(self.decrease_setting, key))
        setting.children[2].bind(on_press=partial(self.increase_setting, key))
        setting.children[0].bind(on_press=partial(self.delete_setting, key))
        return setting


    def show_settings(self):
        self.player.state = 'pause'
        height = 30 # Default height for widgets in the pop-up
        # create content to add to the pop-up

        # First add in all of the current settings

        root = BoxLayout(orientation='vertical',
                         size_hint=(1, 1),
                         padding=10)

        # Add a Scroll View in case the settings need to be scrolled
        scroll = ScrollView(do_scroll_x=False,
                            size=(Window.width, Window.height - height),
                            id='settings_parent')
        self.settings_container = scroll

        # Update the settings and the view will be automatically updated
        # via the on_temp_grab_keys_function
        self.temp_grab_keys = self.grab_keys

        root.add_widget(scroll)

        action_buttons = BoxLayout(orientation='horizontal',
                                   height=height,
                                   size_hint=(1, 0.1),
                                   pos=(0, 0))

        cancel_button = Button(text='cancel', height=height)
        action_buttons.add_widget(cancel_button)

        save_button = Button(text='save', height=height)


        action_buttons.add_widget(save_button)

        root.add_widget(action_buttons)

        settings_popup = Popup(title='Settings',
                               content=root,
                               auto_dismiss=False)

        def save(_):
            """Save the settings on the root screen and dismiss this modal"""
            self.update_settings()
            self.temp_grab_keys = {}
            # Write the settings out to a more permanent file
            file_out = open(self.settings_dir, 'w+')
            file_out.write(json.dumps(self.grab_keys))
            file_out.close()
            settings_popup.dismiss()

        save_button.bind(on_press=save)

        def cancel(_):
            self.temp_grab_keys = {}
            settings_popup.dismiss()
        # bind the on_press event of the button to the dismiss function
        cancel_button.bind(on_press=cancel)

        settings_popup.open()

class LoadDialog(App):

    def build(self):
        return Builder.load_file('LoadDialog.kv')

    def load(self, path, filename):
        video_file = os.path.join(path, filename[0])
        print 'Video file: ', video_file
        App.get_running_app().stop()
        EzyGrab(video_file).run()

if __name__ == '__main__':
    if not sys.argv[1:]:
        LoadDialog().run()
    else:
        EzyGrab(sys.argv[1]).run()
