# window.py
#
# Copyright 2020 Rafael Mardojai CM
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from gettext import gettext as _
from gi.repository import GLib, Gtk, Handy

from .sound import MainPlayer, SoundObject
from .widgets import SoundsGroup
from .settings import Settings

SOUNDS = [
    {
        'name': _('Nature'),
        'sounds': [
            {
                'name': 'rain',
                'title': _('Rain')
            },
            {
                'name': 'storm',
                'title': _('Storm')
            },
            {
                'name': 'wind',
                'title': _('Wind')
            },
            {
                'name': 'summer-night',
                'title': _('Summer Night')
            }
        ]
    },
    {
        'name': _('Interiors'),
        'sounds': [
            {
                'name': 'coffee-shop',
                'title': _('Coffee Shop')
            },
            {
                'name': 'fireplace',
                'title': _('Fireplace')
            }
        ]
    },
    {
        'name': _('Noise'),
        'sounds': [
            {
                'name': 'pink-noise',
                'title': _('Pink Noise')
            },
            {
                'name': 'white-noise',
                'title': _('White Noise')
            }
        ]
    }
]

@Gtk.Template(resource_path='/com/rafaelmardojai/Blanket/window.ui')
class BlanketWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'BlanketWindow'

    box = Gtk.Template.Child()

    playpause_btn = Gtk.Template.Child()
    playpause_icon = Gtk.Template.Child()

    volume = Gtk.Template.Child()

    quit_revealer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Settings wrapper
        self.settings = Settings()
        self.settings.migrate_json() # Migrate old json settings

        # App playing state
        self.playing = self.settings.gsettings.get_boolean('playing')
        self.first_play = True
        self.saved_volume = self.settings.gsettings.get_double('volume')

        # App main player
        self.mainplayer = MainPlayer()

        # Setup widgets
        self.setup()

    def setup(self):
        # Connect vulume scale to volume function
        self.volume.connect('value-changed', self._on_change_vol)
        # Set saved volume value to menu scale
        self.volume.set_value(self.saved_volume)
        self._on_change_vol(self.volume)

        # First run of on_playpause_toggle to setup all
        self.on_playpause_toggle()

        # If background-playback enabled show quit action on menu
        if self.settings.gsettings.get_value('background-playback'):
            self.quit_revealer.set_reveal_child(True)

        # Setup included/saved sounds
        self.setup_sounds()
        self.setup_custom_sounds()

        # Show all widgets added to window
        self.show_all()

    def setup_sounds(self):
        # Setup default sounds
        for g in SOUNDS:
            # Create a new SoundsGroup
            group = SoundsGroup(g['name'], self.settings)
            # Iterate sounds
            for s in g['sounds']:
                # Create a new SoundObject
                sound = SoundObject(s['name'], title=s['title'],
                                    mainplayer=self.mainplayer)
                # Add SoundObject to SoundsGroup
                group.add(sound)

            # Add SoundsGroup to the window's main box
            self.box.pack_start(group, False, True, 0)

    def setup_custom_sounds(self):
        # Setup user custom sounds
        self.custom_sounds = SoundsGroup(_('Custom'), self.settings)
        self.box.pack_start(self.custom_sounds, False, True, 0)

        # Add sound button row
        add_row = Gtk.ListBoxRow()
        add_row.set_selectable(False)
        add_row_box = Gtk.Box(
            height_request = 34
        )
        add_row.add(add_row_box)
        add_row_icon = Gtk.Image.new_from_icon_name(
            'list-add-symbolic',
            Gtk.IconSize.MENU
        )
        add_row_box.pack_start(add_row_icon, True, True, 0)
        self.custom_sounds.listbox.add(add_row)
        self.custom_sounds.listbox.connect('row-activated', self.open_audio)

        # Load saved custom audios
        # Get saved audios from settings
        saved = self.settings.get_custom_audios()
        # Iterate audios
        for name, uri in saved.items():
            # Create a new SoundObject
            sound = SoundObject(name, uri,
                    icon='com.rafaelmardojai.Blanket-sound-wave',
                    removable=True, mainplayer=self.mainplayer)
            # Add SoundObject to SoundsGroup
            self.custom_sounds.add(sound)

    def on_playpause_toggle(self, _widget=None):
        # Change mainplayer mute
        self.mainplayer.set_muted(self.playing)

        # Reverse self.playing bool value
        if not self.first_play:
            self.playing = False if self.playing else True

        # Save playing state
        self.settings.gsettings.set_value('playing',
                                          GLib.Variant('b', self.playing))

        # Change widgets states
        if self.playing:
            self.playpause_icon.set_from_icon_name(
                    'media-playback-pause-symbolic', Gtk.IconSize.MENU)
            self.box.set_sensitive(True)
        else:
            self.playpause_icon.set_from_icon_name(
                    'media-playback-start-symbolic', Gtk.IconSize.MENU)
            self.box.set_sensitive(False)

        self.first_play = False

    def open_audio(self, _widget=None, _row=None):

        filters = {
            'OGG'  : ['audio/ogg'],
            'FLAC' : ['audio/x-flac'],
            'WAV'  : ['audio/x-wav', 'audio/wav'],
            'MP3'  : ['audio/mpeg'],
        }

        self.filechooser = Gtk.FileChooserNative.new(
            _('Open audio'),
            self,
            Gtk.FileChooserAction.OPEN,
            None,
            None)

        for f, mts in filters.items():
            audio_filter = Gtk.FileFilter()
            audio_filter.set_name(f)
            for mt in mts:
                  audio_filter.add_mime_type(mt)
            self.filechooser.add_filter(audio_filter)

        response = self.filechooser.run()

        if response == Gtk.ResponseType.ACCEPT:
            filename = self.filechooser.get_filename()
            if filename:
                name = os.path.basename(filename).split('.')[0]
                uri = self.filechooser.get_uri()

                # Create a new SoundObject
                sound = SoundObject(name, uri,
                    icon='com.rafaelmardojai.Blanket-sound-wave',
                    removable=True, mainplayer=self.mainplayer)
                # Save to settings
                GLib.idle_add(self.settings.add_custom_audio,
                              sound.name, sound.uri)
                # Add SoundObject to SoundsGroup
                self.custom_sounds.add(sound)
                self.custom_sounds.show_all()

    def _on_change_vol(self, scale):
        # Round volume value
        volume = round(scale.get_value(), 2)
        # Set mainplayer volume
        self.mainplayer.set_volume(volume)
        # Save volume on settings
        self.settings.gsettings.set_double('volume', volume)


