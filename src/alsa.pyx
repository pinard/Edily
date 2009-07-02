# Interface to `mymidikbd.c' routines.

cdef extern from *:
    int seq_client
    int seq_open(int device)
    int seq_close()
    void note_on(int pitch, int velocity)
    void note_off(int pitch, int velocity)

def open(int device=128):
    seq_open(device)

def close():
    seq_close()

def note(int sounded, int pitch, int velocity):
    if sounded:
        note_on(pitch, velocity)
    else:
        note_off(pitch, velocity)

    
