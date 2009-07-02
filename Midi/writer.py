#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

class FileWriter(midi.Encoder):
    def __init__(self, write):
        Encoding.__init__(self, write)

    def header(self, header):
        self.write('MThd')
        self.encode_infix(2, header.midi_file_format)
        self.encode_infix(2, header.number_of_tracks)
        self.encode_infix(2, header.division)

    def delay(self, delta):
        if not mute:
            self.encode_intvar(delta)

    # FIXME: Not written yet.
