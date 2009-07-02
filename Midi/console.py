#!/usr/bin/env python
# -*- coding: Latin-1 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

import midi

class Console(midi.Player):
    # Standard Input must be associated to a virtual terminal.

    # The musical ear is not tolerant at all to frequency errors, yet it
    # strangely makes some sense with music despite wide errors in duration,
    # at least given that the overall beat organisation is respected.  This
    # is the idea behind this console beep player, admittedly a toy! :-) It
    # nevertheless could be used to debug MIDI scores without a sound card.

    # Start sound generation (0 for off) -- value from <linux/kd.h>.
    KIOCSOUND = 0x4B2F
    # Pseudo-sampling rate of the beeper console, first found
    # experimentally, then corrected (-100) by peeking into kernel sources.
    sampling_rate = 1193180
    # HASHING is the time per voice for hashed multi-voice play.  A too
    # short HASHING would introduce a low frequency noisy sound, a too long
    # long HASHING would destroy the attempt at a polyphonic effect.
    minimum_hashing = .060
    maximum_hashing = .110
    # If True, hash even a single voice.  There is a problem when False,
    # which I do not understand: maybe `time.sleep()' then gets interrupted?
    hash_single_voice = True
    # Number of supported octaves.
    number_of_octaves = 13
    # Zero based ordinal of the middle octave.
    middle_octave = 5
    # Frequencies in Hertz of the chromatic scale, from C3 to B4, for an equal
    # temperament, tuned to a 440 diapason.
    chromatic_scale = (
        523.25, 554.37, 587.33, 622.25, 659.26, 698.46, 739.99, 783.99,
        830.61, 880.00, 932.33, 987.77)

    def __init__(self):
        midi.Player.__init__(self)
        # Wave numbers are proportional to wave lengths.
        self.wave_number = [None] * (Console.number_of_octaves * 12)
        # Initialize the main scale.
        for base in range(12):
            pitch = Console.middle_octave * 12 + base
            self.wave_number[pitch] = int(
                Console.sampling_rate / Console.chromatic_scale[base])
        # Initialize octaves and suboctaves.
        for pitch in range(Console.middle_octave * 12 - 1, -1, -1):
            self.wave_number[pitch] = self.wave_number[pitch + 12] * 2
        for pitch in range((Console.middle_octave + 1) * 12,
                           Console.number_of_octaves * 12):
            self.wave_number[pitch] = self.wave_number[pitch - 12] // 2
        # All sound pitches never heard at least once.
        self.urgent = []
        # All sound pitches currently played, including URGENT.
        self.pitches = []
        # ROVER gives the current PITCHES index, it is global for all sounds.
        # This increases the probability that all sounds are equally heard.
        self.rover = None

    def close(self):
        if self.opened:
            import fcntl, sys
            # Silence the last sound.
            fcntl.ioctl(sys.stderr, Console.KIOCSOUND, 0)
            self.opened = False

    def delay(self, delta):
        if midi.run.mute:
            return
        import fcntl, sys, time
        self.goal += delta * self.time_rate
        if not self.pitches:
            # Silence the last sound.
            fcntl.ioctl(sys.stderr, Console.KIOCSOUND, 0)
            now = time.time()
            while now < self.goal:
                time.sleep(self.goal - now)
                now = time.time()
            return
        # Play all sounds from the PITCHES array, hashing them to achieve
        # multi-voice effect, but no more than HASHING seconds at a time.
        # Guarantee that urgent sounds are heard at least once, even if
        # this makes us a bit late.  Hopefully, we will catch up later.
        dividend = max(self.goal - time.time(), Console.minimum_hashing)
        divider = len(self.pitches)
        if len(self.pitches) > 1 or Console.hash_single_voice:
            hashing = dividend / divider
            while hashing > Console.maximum_hashing:
                hashing *= .5
            while hashing < Console.minimum_hashing and divider > 1:
                divider -= 1
                hashing = dividend / divider
            #if divider == len(self.pitches):
            #    self.rover = 0
        if self.urgent:
            self.urgent.sort()
            for pitch in self.urgent:
                # Start sound.
                fcntl.ioctl(sys.stderr, Console.KIOCSOUND,
                            self.wave_number[pitch])
                time.sleep(hashing)
        now = time.time()
        while now < self.goal:
            pitch = self.pitches[self.rover]
            if pitch in self.urgent:
                self.urgent.remove(pitch)
            else:
                # Start sound.
                fcntl.ioctl(sys.stderr, Console.KIOCSOUND,
                            self.wave_number[pitch])
                time.sleep(hashing)
                now = time.time()
            self.rover += 1
            if self.rover == len(self.pitches):
                self.rover = 0
        self.urgent = []

    def note_off(self, track, channel, pitch, velocity):
        if channel == midi.run.drum_channel or pitch not in self.pitches:
            return
        index = self.pitches.index(pitch)
        del self.pitches[index]
        if self.rover > index:
            self.rover -= 1
        elif self.rover == index == len(self.pitches):
            if self.pitches:
                self.rover = 0
            else:
                self.rover = None

    def note_on(self, track, channel, pitch, velocity):
        if velocity == 0:
            self.note_off(track, channel, pitch, 0)
            return
        if midi.run.mute:
            return
        if channel == midi.run.drum_channel:
            return
        if pitch in self.pitches:
            return
        if 0 < pitch < Console.number_of_octaves * 12:
            self.urgent.append(pitch)
            if self.pitches:
                from bisect import bisect
                index = bisect(self.pitches, pitch)
                self.pitches.insert(index, pitch)
                if self.rover >= index:
                    self.rover += 1
            else:
                self.pitches.append(pitch)
                self.rover = 0
