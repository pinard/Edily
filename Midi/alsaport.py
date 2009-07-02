#!/usr/bin/env python
# -*- coding: Latin-1 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

import midi

class AlsaPort(midi.Player):
    def __init__(self, device=128):
        midi.Player.__init__(self)
        import alsa
        self.alsa = alsa
        alsa.open(device)
        # Notes being sound, so we can silence them at close time.
        self.notes = {}

    def close(self):
        if self.opened:
            for channel, pitch in self.notes.keys():
                self.note_off(None, channel, pitch, 127)
            self.alsa.close()
            self.opened = False

    def note_off(self, track, channel, pitch, velocity):
        self.alsa.note(False, pitch, velocity)
        key = channel, pitch
        if key in self.notes:
            del self.notes[key]

    def note_on(self, track, channel, pitch, velocity):
        self.alsa.note(True, pitch, velocity)
        key = channel, pitch
        if velocity == 0:
            if key in self.notes:
                del self.notes[key]
        else:
            self.notes[key] = None
