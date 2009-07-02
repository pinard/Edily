#!/usr/bin/env python
# -*- coding: Latin-1 -*-
# Copyright © 1995, 1998, 2000, 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>.

"""\
Play a MIDI file.

Usage: joue [OPTION]... [INPUT]

Mandatory arguments to long options are mandatory for short options too.

  -b, --bars=EXCERPT     play bars according to EXCERPT specification
  -c, --check            check MIDI file without performing it
  -s, --speed=FACTOR     adjust speed, bigger the slower, default is 100
  -f, --freeze-channel   inhibit all program changes
  -z, --channel-zero     force all notes on channel zero
  -t, --transpose=NUM    number of semi-tones of transposition
  -d, --drum=CHANNEL     drum channel, not to be transposed, default is 9
  -D, --debug=BITS       turn on debug bits, default is 8
  -k, --console          use console beeper simultaneously to MIDI port
      --help             display this help and exit
      --version          output version information and exit

BITS are 1 deltas, 2 MIDI notes, 4 other MIDI events, 8 meta-events.
EXCERPT is [FACTORx][[FIRST]-][LAST] to select from FIRST bar to LAST bar,
both counted from 1, and LAST included.  FACTOR says how many beats per bar,
defaulting to 1.  Play from beginning if FIRST is omitted, through end if
LAST is omitted.  If only LAST is given, play only that bar.

With no FILE or if FILE is -, read Standard Input.  Files suffixed with
`.gz' files are automatically uncompressed.
"""

import sys

#  -m, --map=IN..OUT      map IN selection into OUT selection

def main(*arguments):
    import midi
    # Decode program options.
    check_mode = False
    console = False
    debug = midi.DUMP_METAS
    import getopt
    options, arguments = getopt.getopt(
        arguments, 'D:b:cd:fkm:s:t:x:z',
        ('bars=', 'channel-zero', 'check', 'console', 'debug=', 'drum=',
         'extract=', 'freeeze-channel', 'help', 'map=' 'speed=',
         'transpose=', 'version'))
    for option, value in options:
        if option == '--help':
            sys.stdout.write(__doc__)
            sys.exit(0)
        if option == '--version':
            from Midi import __package__, __version__
            sys.stdout.write("Free %s %s\n" % (__package__, __version__))
            sys.exit(0)
        if option in ('-D', '--debug'):
            debug = int(value)
        elif option in ('-b', '--bars'):
            decode_bars(value)
        elif option in ('-c', '--check'):
            check_mode = True
        elif option in ('-d', '--drum'):
            midi.run.drum_channel = int(value)
        elif option in ('-f', '--freeze_channel'):
            midi.run.freeze_channel = True
        elif option in ('-k', '--console'):
            console = True
        elif option in ('-m', '--map'):
            pass
        elif option in ('-s', '--speed'):
            midi.run.speed_factor = int(value)
        elif option in ('-t', '--transpose'):
            midi.run.transpose = int(value)
        elif option in ('-x', '--extract'):
            midi.run.extract = int(value)
        elif option in ('-z', '--channel-zero'):
            midi.run.channel_zero = True
    # Launch wanted processing.
    if not arguments:
        midi_file = midi.Decoder(sys.stdin)
    elif len(arguments) == 1:
        if arguments[0].endswith('.gz'):
            import gzip
            midi_file = midi.Decoder(gzip.open(arguments[0]))
        else:
            midi_file = midi.Decoder(file(arguments[0]))
    else:
        usage()
    if check_mode:
        from dumper import Dumper
        midi_file.serial_process(Dumper(flags=debug))
    else:
        from midiport import MidiPort
        if debug or console:
            processor = midi.MultiProcessor()
            if debug:
                from dumper import Dumper
                processor.add(Dumper(flags=debug))
            if console:
                from console import Console
                processor.add(Console())
            processor.add(MidiPort())
        else:
            processor = MidiPort()
        midi_file.parallel_process(processor)

def decode_bars(argument):
    import re
    import midi
    match = re.match(r'([0-9]+x)?([0-9]*-)?([0-9]+)?$', argument)
    if match is None:
        usage()
    if match.group(1) is not None:
        midi.run.beats_per_bar = int(match.group(1)[:-1]) or 1
    if match.group(2) is not None:
        start = int(match.group(2)[:-1])
        if start > 0:
            start -= 1
        midi.run.start_bar = start
        if match.group(3) is not None:
            end = int(match.group(3))
            if end > 0:
                end -= 1
            midi.run.end_bar = end + 1
    elif match.group(3) is not None:
        start = int(match.group(3))
        if start > 0:
            start -= 1
        midi.run.start_bar = start
        midi.run.end_bar = start + 1
    sys.stderr.write("** %s %s\n" % (midi.run.start_bar, midi.run.end_bar))

def usage():
    sys.stderr.write("Try `joue --help' for more information.\n")
    sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])
