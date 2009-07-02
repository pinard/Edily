#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

import midi

class MidiPort(midi.Player, midi.Encoder):
    def __init__(self, device=None):
        if device is None:
            device = '/dev/midi'
        midi.Player.__init__(self)
        self.device = file(device, 'w')
        midi.Encoder.__init__(self, self.write)
        # Notes being sound, so we can silence them at close time.
        self.notes = {}

    def close(self):
        if self.opened:
            for channel, pitch in self.notes.keys():
                self.note_off(None, channel, pitch, 127)
            self.device.close()
            self.opened = False

    def write(self, bytes):
        self.device.write(bytes)
        self.device.flush()

    def delay(self, delta):
        #if not run.mute and self.running_status is not None:
        #if self.running_status is not None:
        #    self.device.flush()
        midi.Player.delay(self, delta)

    def note_off(self, track, channel, pitch, velocity):
        midi.Encoder.note_off(self, track, channel, pitch, velocity)
        key = channel, pitch
        if key in self.notes:
            del self.notes[key]

    def note_on(self, track, channel, pitch, velocity):
        midi.Encoder.note_on(self, track, channel, pitch, velocity)
        key = channel, pitch
        if velocity == 0:
            if key in self.notes:
                del self.notes[key]
        else:
            self.notes[key] = None

    # Do not encode the following events, despite an encoding exists.

    def set_status(self, track, event):
        pass
    def meta_event_text(self, track, text, message):
        pass
    def meta_event_binary(self, track, bytes, message):
        pass
    def end_of_track(self, track):
        pass
    def undefined(self, track, buffer):
        pass
