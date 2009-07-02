# MIDI tools for Python - Makefile.
# Copyright © 2003 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>, 2003-06.

PYSETUP = python setup.py
DISTRIBUTION = Midi-0.2

all:
	$(PYSETUP) build

install: all
	$(PYSETUP) install

tags:
	(find bin -type f; find -name '*.py') | grep -v '~$$' | etags -

dist:
	$(PYSETUP) sdist
	mv dist/$(DISTRIBUTION).tar.gz .
	rmdir dist
	ls -l *.gz

publish: dist
	traiter README.html > index.html
	chmod 644 index.html $(DISTRIBUTION).tar.gz
	scp -p index.html $(DISTRIBUTION).tar.gz bor:w/midi/
	rm index.html $(DISTRIBUTION).tar.gz
	ssh bor rm -vf w/midi/Midi.tar.gz
	ssh bor ln -vs $(DISTRIBUTION).tar.gz w/midi/Midi.tar.gz
	ssh bor ls -Llt w/midi

rawmidi: src/rawmidi.c
	cc -g -o rawmidi src/rawmidi.c -lasound
