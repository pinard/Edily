#!/usr/bin/env python
# -*- coding: Latin-1 -*-

import sys
sys.path.insert(0, '.')
from Midi import __package__, __version__
del sys.path[0]

from distutils.core import setup
from distutils.extension import Extension
from Pyrex.Distutils import build_ext

alsa = Extension('Midi.alsa',
                 ['src/alsa.pyx', 'src/mymidikbd.c'],
                 libraries=['asound'])

setup(name=__package__, version=__version__,
      description="MIDI tools for Python.",
      author='François Pinard', author_email='pinard@iro.umontreal.ca',
      url='http://www.iro.umontreal.ca/~pinard',
      ext_modules=[alsa], cmdclass={'build_ext': build_ext},
      scripts=['joue'], packages=['Midi'])
