#!/usr/bin/env python
# -*- coding: Latin-1 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

import midi

class Verbose(midi.Processor):
    def __init__(self, write=None, flags=0):
        if write is None:
            import sys
            write = sys.stderr.write
        self.write = write
        self.flags = flags
        self.bar = 0

    def header(self, header):
        self.write("Format %d, division %d\n"
                   % (header.midi_file_format, header.division))

    def delay(self, delta):
        if not midi.run.mute:
            if midi.run.bar != self.bar:
                if midi.run.beats_per_bar == 1:
                    self.write("%% beat %d\n" % (midi.run.bar + 1))
                else:
                    self.write("%% bar %d\n" % (midi.run.bar + 1))
                self.bar = midi.run.bar
        if self.flags & midi.DUMP_DELTAS:
            self.write('%4d  ' % delta)

    def meta_event_text(self, track, text, message):
        if self.flags & midi.DUMP_METAS:
            self.write('trk%-2d %s: %s\n'
                       % (track.number, message, text.rstrip()))

    def meta_event_binary(self, track, bytes, message):
        if self.flags & midi.DUMP_METAS:
            write = self.write
            write('trk%-2d %s:' % (track.number, message))
            for byte in bytes:
                write(' %02x' % byte)
            write('\n')

class Dumper(Verbose):

    def note_off(self, track, channel, pitch, velocity):
        if self.flags & midi.DUMP_NOTES:
            self.write('trk%-2d ch%-2d off %d %d\n'
                       % (track.number, channel, pitch, velocity))

    def note_on(self, track, channel, pitch, velocity):
        if self.flags & midi.DUMP_NOTES:
            if velocity == 0:
                self.write('trk%-2d ch%-2d off %d\n'
                           % (track.number, channel, pitch))
            else:
                self.write('trk%-2d ch%-2d on %d %d\n'
                           % (track.number, channel, pitch, velocity))

    def key_pressure(self, track, channel, pitch, pressure):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d ch%-2d key-pressure %d %d\n'
                       % (track.number, channel, pitch, pressure))

    def parameter(self, track, channel, parameter, setting):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d ch%-2d parameter %d %d\n'
                       % (track.number, channel, parameter, setting))

    def program(self, track, channel, program):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d ch%-2d program %d\n'
                       % (track.number, channel, program))

    def channel_pressure(self, track, channel, pressure):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d ch%-2d channel-pressure %d\n'
                       % (track.number, channel, pressure))

    def pitch_wheel(self, track, channel, wheel):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d ch%-2d pitch-wheel %d\n'
                       % (track.number, channel, wheel))

    def sysex(self, track, bytes, continuation=False):
        if continuation:
            message = 'sysex-cont'
        else:
            message = 'sysex'
        parse_bytes (track, parse_intvar (track),
                     self.flags & midi.DUMP_EVENTS, message)

    def end_of_track(self, track):
        if self.flags & midi.DUMP_METAS:
            self.write('trk%-2d End of Track\n' % track.number)

    def set_tempo(self, track, tempo):
        if self.flags & midi.DUMP_METAS:
            self.write('trk%-2d Set Tempo %d\n' % (track.number, tempo))

    def undefined(self, track, buffer):
        if self.flags & midi.DUMP_EVENTS:
            self.write('trk%-2d Undefined %02x:' % (track.number, event))
            #while (...):
            #    write(' %02x' % ord(self.buffer[self.position]))
