AUTOMAKE_OPTIONS = gnits
noinst_HEADERS = system.h
bin_PROGRAMS = joue
joue_SOURCES = joue.c

INCLUDES = -I.. -I$(srcdir) -I$(top_srcdir)/lib
LIBS = ../lib/libjoue.a

mididir = $(HOME)/pub/midi
MIDIFILES = $(mididir)/*.mid.gz
MIDICAT = cat $(top_srcdir)/fugue.mid
#MIDICAT = cat $(mididir)/sweat.mid
#MIDICAT = cat $(mididir)/all_she_wants.mid
#MIDICAT = cat $(mididir)/gs-guant.mid
#MIDICAT = gunzip < $(mididir)/silent2.mid.gz
#MIDICAT = gunzip < $(mididir)/wildthing.mid.gz
#MIDICAT = cat $(HOME)/pub/midi0/general_midi/whenifal.mid
#MIDICAT = gunzip < $(mididir)/MT-32/yahoo32.mid.gz
FLAGS =

essai0: joue
	$(MIDICAT) | ./joue $(FLAGS)

essai: joue
	for file in $(MIDIFILES); do gunzip < $$file | ./joue || exit 1; done
