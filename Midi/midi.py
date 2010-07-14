#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

DUMP_DELTAS =  1 << 0
DUMP_NOTES = 1 << 1
DUMP_EVENTS = 1 << 2                    # MIDI events except notes on/off
DUMP_METAS = 1 << 3

class run:
    pass

def reset():
    # Program options.
    run.freeze_channel = False
    run.channel_zero = False
    run.drum_channel = 9
    run.speed_factor = 100
    run.transpose = 0
    run.extract = None
    run.beats_per_bar = 1
    run.start_bar = None                # included, counted from 0
    run.end_bar = None                  # excluded, counted from 0
    # Run-time variables.
    run.mute = False
    run.bar = None                      # bar number in file, counted from 0

reset()

class Decoder:

    def __init__(self, input):
        buffer = input.read()
        self.header = Header(buffer)
        position = self.header.limit
        self.tracks = []
        for counter in range(self.header.number_of_tracks):
            track = Track(buffer, position, counter + 1)
            position = track.limit
            if run.extract is None or run.extract == track.number:
                self.tracks.append(track)
        assert position == len(buffer), (position, len(buffer))

    def serial_process(self, processor):
        processor.header(self.header)
        for track in self.tracks:
            track.rewind()
            while track.delta is not None:
                processor.delay(track.delta)
                track.dispatch_event(processor)

    def parallel_process(self, processor):
        processor.header(self.header)
        for track in self.tracks:
            track.rewind()
        run.bar = 0
        run.beat = 0
        tics_per_bar = self.header.division * run.beats_per_bar
        tics = 0
        while True:
            delta = None
            for track in self.tracks:
                if track.delta is not None:
                    if delta is None or track.delta < delta:
                        delta = track.delta
            if delta is None:
                break
            tics += delta
            bars, tics = divmod(tics, tics_per_bar)
            run.bar += bars
            run.mute = (
                (run.start_bar is not None and run.bar < run.start_bar)
                or (run.end_bar is not None and run.bar >= run.end_bar))
            processor.delay(delta)
            for track in self.tracks:
                if track.delta is not None:
                    track.delta -= delta
                    while track.delta == 0:
                        track.dispatch_event(processor)

class Chunk:

    def __init__(self, magic, buffer, position, number):
        assert buffer[position:position+4] == magic, (
            buffer[position:position+4], magic)
        self.buffer = buffer            # whole file buffer
        self.start = position           # start index for MIDI chunk
        position += 4
        assert position+4 <= len(self.buffer), len(self.buffer)
        value = 0
        for counter in range(4):
            value = (value << 8) | ord(self.buffer[position])
            position += 1
        self.position = position        # buffer index of next unparsed byte
        self.limit = position + value   # buffer index for end of this chunk
        assert self.limit <= len(buffer), (self.limit, len(buffer))
        self.number = number            # track number for printing

class Header(Chunk):

    def __init__(self, buffer):
        Chunk.__init__(self, 'MThd', buffer, 0, 0)
        self.midi_file_format = self.decode_intfix_2()
        assert 0 <= self.midi_file_format <= 2, self.midi_file_format
        self.number_of_tracks = self.decode_intfix_2()
        self.division = self.decode_intfix_2()
        assert self.position == self.limit, (self.position, self.limit)

    def decode_intfix_2(self):
        position = self.position
        assert position + 2 <= self.limit, (position, self.limit)
        value = ((ord(self.buffer[position]) << 8)
                 | ord(self.buffer[position+1]))
        self.position = position + 2
        return value

class Track(Chunk):

    def __init__(self, buffer, position, track):
        Chunk.__init__(self, 'MTrk', buffer, position, track)
        self.running_status = None      # running status after last event
        self.delta = None               # delta time value before event

    def rewind(self, speed_factor=1):
        self.position = self.start + 8
        # Default to piano on channel 1.
        self.running_status = 0
        self.next_delta()

    def next_delta(self):
        if self.position < self.limit:
            self.delta = self.decode_intvar()
        else:
            self.delta = None

    def dispatch_event(self, processor):
        # Parse one event, which is a MIDI event, a sysex event or a
        # meta-event.  MIDI events cover voice messages only, as system
        # messages and real time messages do not occur in MIDI files.
        assert self.position < self.limit, (self.position, self.limit)
        byte = ord(self.buffer[self.position])
        if byte & 0x80:
            # Possibly alter running status.
            if run.channel_zero and (byte & 0xf0) != 0xf0:
                byte &= 0xf0
            event = byte
            self.position += 1
            if event < 0xf0:
                self.running_status = event
        else:
            # Use previous running status.
            assert self.running_status is not None
            event = self.running_status
            processor.set_status(self, event)
        nibble = event & 0xf0
        if nibble == 0x80:
            # MIDI event: note off.
            channel = self.running_status & 0x0f
            pitch = self.decode_int7()
            if channel != run.drum_channel:
                pitch += run.transpose
            velocity = self.decode_int7()
            if pitch > 0:
                processor.note_off(self, channel, pitch, velocity)
            self.next_delta()
            return
        if nibble == 0x90:
            # MIDI event: note on.
            channel = self.running_status & 0x0f
            pitch = self.decode_int7()
            if channel != run.drum_channel:
                pitch += run.transpose
            velocity = self.decode_int7()
            if pitch > 0:
                processor.note_on(self, channel, pitch, velocity)
            self.next_delta()
            return
        if nibble == 0xa0:
            # MIDI event: key pressure.
            channel = self.running_status & 0x0f
            pitch = self.decode_int7()
            if channel != run.drum_channel:
                pitch += run.transpose
            pressure = self.decode_int7()
            if pitch > 0:
                processor.key_pressure(self, channel, pitch, pressure)
            self.next_delta()
            return
        if nibble == 0xb0:
            # MIDI event: parameter.
            channel = self.running_status & 0x0f
            parameter = self.decode_int7()
            setting = self.decode_int7()
            processor.parameter(self, channel, parameter, setting)
            self.next_delta()
            return
        if nibble == 0xc0:
            # MIDI event: program.
            channel = self.running_status & 0x0f
            program = self.decode_int7()
            if not run.freeze_channel:
                processor.program(self, channel, program)
            self.next_delta()
            return
        if nibble == 0xd0:
            # MIDI event: channel pressure.
            channel = self.running_status & 0x0f
            pressure = self.decode_int7()
            processor.channel_pressure(self, channel, pressure)
            self.next_delta()
            return
        if nibble == 0xe0:
            # MIDI event: pitch wheel.
            channel = self.running_status & 0x0f
            wheel = self.decode_int14() - 0x2000
            processor.pitch_wheel(self, channel, wheel)
            self.next_delta()
            return
        if nibble == 0xf0:
            self.running_status = None
            if event == 0xf0:
                # Sysex event.
                bytes = self.decode_bytes(self.decode_intvar())
                processor.sysex(self, bytes, False)
                self.next_delta()
                return
            if event == 0xf7:
                # Sysex event (continuation).
                bytes = self.decode_bytes (self.decode_intvar())
                processor.sysex(self, bytes, True)
                self.next_delta()
                return
            if event == 0xff:
                # Meta-event.
                event = self.decode_int7()
                length = self.decode_intvar()
                if event == 0x01:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Text")
                    self.next_delta()
                    return
                if event == 0x02:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Copyright")
                    self.next_delta()
                    return
                if event == 0x03:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Sequence/Track")
                    self.next_delta()
                    return
                if event == 0x04:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Instrument")
                    self.next_delta()
                    return
                if event == 0x05:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Lyric")
                    self.next_delta()
                    return
                if event == 0x06:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Marker")
                    self.next_delta()
                    return
                if event == 0x07:
                    text = self.decode_text(length)
                    processor.meta_event_text(self, text, "Cue")
                    self.next_delta()
                    return
                if event == 0x2f:
                    # End of track.
                    assert length == 0, length
                    processor.end_of_track(self)
                    self.next_delta()
                    return
                if event == 0x51:
                    # Set Tempo.
                    assert length == 3, length
                    tempo = self.decode_intfix(3)
                    processor.set_tempo(self, tempo)
                    self.next_delta()
                    return
                if event == 0x54:
                    bytes = self.decode_bytes(length)
                    processor.meta_event_binary(self, bytes, "SMPTE Offset")
                    self.next_delta()
                    return
                if event == 0x58:
                    bytes = self.decode_bytes(length)
                    processor.meta_event_binary(self, bytes, "Time Signature")
                    self.next_delta()
                    return
                if event == 0x59:
                    bytes = self.decode_bytes(length)
                    processor.meta_event_binary(self, bytes, "Key Signature")
                    self.next_delta()
                    return
                if event == 0x7f:
                    bytes = self.decode_bytes(length)
                    processor.meta_event_binary(self, bytes,
                                                "Sequencer-Specific")
                    self.next_delta()
                    return
                bytes = self.decode_bytes(length)
                processor.meta_event_binary(self, bytes,
                                            "Meta Event %02x" % event)
                self.next_delta()
                return
            # Undefined.
            position = self.position
            counter = 1
            while position+counter < self.limit:
                if ord(self.buffer[position+counter]) & 0x80:
                    break
            processor.undefined(self, event,
                                self.buffer[position:position+counter])
            self.position = position + counter
            self.next_delta()

    def next_delta(self):
        if self.position < self.limit:
            self.delta = self.decode_intvar()
        else:
            self.delta = None

    def decode_int7(self):
        assert self.position < self.limit, (self.position, self.limit)
        assert ord(self.buffer[self.position]) & 0x80 == 0, (
            self.position, ord(self.buffer[self.position]))
        value = ord(self.buffer[self.position])
        self.position += 1
        return value

    def decode_int14(self):
        assert self.position+2 <= self.limit, (self.position, self.limit)
        assert ord(self.buffer[self.position]) & 0x80 == 0, (
            self.position, ord(self.buffer[self.position]))
        assert ord(self.buffer[self.position+1]) & 0x80 == 0, (
            self.position+1, ord(self.buffer[self.position+1]))
        value = ((ord(self.buffer[self.position]) << 7)
                 | ord(self.buffer[self.position+1]))
        self.position += 2
        return value

    def decode_intfix(self, length):
        assert self.position+length <= self.limit, (self.position, self.limit)
        value = 0
        for counter in range(length):
            value = (value << 8) | ord(self.buffer[self.position])
            self.position += 1
        return value

    def decode_intvar(self):
        value = 0
        assert self.position < self.limit, (self.position, self.limit)
        while ord(self.buffer[self.position]) & 0x80:
            value = (value << 7) | (ord(self.buffer[self.position]) & 0x7f)
            self.position += 1
            assert self.position < self.limit, (self.position, self.limit)
        value = (value << 7) | ord(self.buffer[self.position])
        self.position += 1
        return value

    def decode_bytes(self, length):
        position = self.position
        assert position+length <= self.limit, (self.position, self.limit)
        bytes = [ord(self.buffer[position+counter])
                 for counter in range(length)]
        self.position = position + length
        return bytes

    def decode_text(self, length):
        position = self.position
        assert position+length <= self.limit, (self.position, self.limit)
        text = self.buffer[position:position+length]
        self.position = position + length
        return text

class Processor:
    def header(self, header):
        pass
    def delay(self, delta):
        pass
    def set_status(self, track, event):
        pass
    def key_pressure(self, track, channel, pitch, pressure):
        pass
    def parameter(self, track, channel, parameter, setting):
        pass
    def program(self, track, channel, program):
        pass
    def channel_pressure(self, track, channel, pressure):
        pass
    def pitch_wheel(self, track, channel, wheel):
        pass
    def sysex(self, track, bytes, continuation=False):
        pass
    def meta_event_text(self, track, text, message):
        pass
    def meta_event_binary(self, track, bytes, message):
        pass
    def end_of_track(self, track):
        pass
    def set_tempo(self, track, tempo):
        pass
    def undefined(self, track, buffer):
        pass

class MultiProcessor:
    def __init__(self):
        self.processors = []
    def add(self, processor):
        self.processors.append(processor)
    #
    def header(self, *arguments):
        self.process('header', arguments)
    def delay(self, *arguments):
        self.process('delay', arguments)
    def set_status(self, *arguments):
        self.process('set_status', arguments)
    def note_off(self, *arguments):
        self.process('note_off', arguments)
    def note_on(self, *arguments):
        self.process('note_on', arguments)
    def key_pressure(self, *arguments):
        self.process('key_pressure', arguments)
    def parameter(self, *arguments):
        self.process('parameter', arguments)
    def program(self, *arguments):
        self.process('program', arguments)
    def channel_pressure(self, *arguments):
        self.process('channel_pressure', arguments)
    def pitch_wheel(self, *arguments):
        self.process('pitch_wheel', arguments)
    def sysex(self, *arguments):
        self.process('sysex', arguments)
    def meta_event_text(self, *arguments):
        self.process('meta_event_text', arguments)
    def meta_event_binary(self, *arguments):
        self.process('meta_event_binary', arguments)
    def end_of_track(self, *arguments):
        self.process('end_of_track', arguments)
    def set_tempo(self, *arguments):
        self.process('set_tempo', arguments)
    def undefined(self, *arguments):
        self.process('undefined', arguments)
    #
    def process(self, function_name, arguments):
        for processor in self.processors:
            getattr(processor, function_name)(*arguments)

class Encoder(Processor):

    def __init__(self, write):
        self.write = write

    def note_off(self, track, channel, pitch, velocity):
        self.encode_byte(0x80 | channel)
        self.encode_int7(pitch)
        self.encode_int7(velocity)

    def note_on(self, track, channel, pitch, velocity):
        self.encode_byte(0x90 | channel)
        self.encode_int7(pitch)
        self.encode_int7(velocity)

    def key_pressure(self, track, channel, pitch, pressure):
        self.encode_byte(0xa0 | channel)
        self.encode_int7(pitch)
        self.encode_int7(pressure)

    def parameter(self, track, channel, parameter, setting):
        self.encode_byte(0xb0 | channel)
        self.encode_int7(parameter)
        self.encode_int7(setting)

    def program(self, track, channel, program):
        self.encode_byte(0xc0 | channel)
        self.encode_int7(program)

    def channel_pressure(self, track, channel, pressure):
        self.encode_byte(0xd0 | channel)
        self.encode_int7(pressure)

    def pitch_wheel(self, track, channel, wheel):
        self.encode_byte(0xe0 | channel)
        self.encode_int14(wheel + 0x2000)

    def sysex(self, track, bytes, continuation=False):
        if continuation:
            self.encode_byte(0xf7)
        else:
            self.encode_byte(0xf0)
        self.encode_intvar(bytes)

    def meta_event_text(self, track, text, message):
        self.encode_byte(0xff)
        self.encode_int7({"Text": 0x01,
                          "Copyright": 0x02,
                          "Sequence/Track": 0x03,
                          "Instrument": 0x04,
                          "Lyric": 0x05,
                          "Marker": 0x06,
                          "Cue": 0x07}.get(message))
        self.encode_intvar(length)
        self.encode_text(text)

    def meta_event_binary(self, track, bytes, message):
        self.encode_byte(0xff)
        self.encode_int7({"SMPTE Offset": 0x54,
                          "Time Signature": 0x58,
                          "Key Signature": 0x59,
                          "Sequencer-Specific": 0x7f}.get(message))
        self.encode_intvar(length)
        self.encode_bytes(bytes)

    def end_of_track(self, track):
        self.encode_byte(0xff)
        self.encode_byte(0x2f)
        self.encode_intvar(0)

    def set_tempo(self, track, tempo):
        self.encode_byte(0xff)
        self.encode_byte(0x51)
        self.encode_intvar(3)
        self.encode_intfix(3, tempo)

    def undefined(self, track, buffer):
        pass

    def encode_byte(self, value):
        assert value < 1<<8, value
        self.write(chr(value))

    def encode_int7(self, value):
        assert value < 1<<7, value
        self.write(chr(value))

    def encode_int14(self, value):
        assert value < 1<<14, value
        self.write(chr(value << 7))
        self.write(chr(value & 0x7f))

    def encode_intfix(self, length, value):
        assert value < 1<<(8*length), (value, length)
        while length > 0:
            length -= 1
            self.write(chr((value >> (8*length)) & 0xff))

    def encode_intvar(self, value):
        shift = 0
        while value >> shift:
            shift += 7
        while shift > 7:
            shift -= 7
            self.write(chr((value >> shift) & 0x7f | 0x80))
        self.write(chr(value & 0x7f))

    def encode_bytes(self, bytes):
        for byte in bytes:
            self.write(chr(byte))

    def encode_text(self, text):
        self.write(text)

class Player(Processor):

    def __init__(self):
        # When ABSOLUTE is True, one second has DIVISION time units.
        # Otherwise, one quarter note has DIVISION time units.
        self.absolute = None
        self.division = None
        # Micro-seconds per quarter note.
        self.tempo = None
        # Opened flag.
        self.opened = True

    def __del__(self):
        if self.opened:
            self.close()

    def header(self, header):
        # Start at 120 quarter notes per minute, that is, 0.5 second per
        # quarter note, and this for when speed_factor is exactly 100.
        self.division = header.division
        self.set_tempo(None, 5000 * run.speed_factor)
        # Reset reference time when processing the MIDI file header.
        import time
        self.goal = time.time()
        #if run.start_bar is None:

    def delay(self, delta):
        # We should wait.  However, the real time moved as this program
        # burns CPU or has been context switched out by the operating
        # system, we might have to adjust the wait for such lags.
        if run.mute:
            return
        self.goal += delta * self.time_rate
        import time
        now = time.time()
        if now < self.goal:
            time.sleep(self.goal - now)

    def set_tempo(self, track, tempo):
        self.time_rate = 1e-8 * tempo * run.speed_factor / self.division
