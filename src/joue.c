/* Study MIDI file formats.
   Copyright © 1995, 1998 Progiciels Bourbeau-Pinard inc.
   François Pinard <pinard@iro.umontreal.ca>.  */

#ifdef HAVE_CONFIG_H
# include <config.h>
#endif

#include "system.h"
#include <sys/time.h>

/* Global definitions.  */

/* EVENTS is MIDI events except notes on/off.  */
#define DUMP_DELTAS	(1 << 0)
#define DUMP_NOTES	(1 << 1)
#define DUMP_EVENTS	(1 << 2)
#define DUMP_METAS	(1 << 3)

/* Reallocation step when swallowing non regular files.  The value is not
   the actual reallocation step, but its base two logarithm.  */
#define SWALLOW_REALLOC_LOG 12

/* The name this program was run with. */
const char *program_name;

/* If non-zero, display usage information and exit.  */
static int show_help = 0;

/* If non-zero, print the version on standard output and exit.  */
static int show_version = 0;

/* Program options.  */
const char *file_name;
bool check_mode = false;
bool freeze_channel = false;
bool channel_zero = false;
int debug_bits = DUMP_METAS;
int drum_channel = 9;
int speed_factor = 100;
int transpose = 0;
int extract = 0;

/* Memory image of the MIDI file.  */
static unsigned char *buffer_start;
/* One byte past memory image.  */
static unsigned char *buffer_limit;
/* Cursor in memory image.  */
static unsigned char *buffer_cursor;
/* Midi file format.  */
int midi_file_format;
/* Decide how to interpret division.  */
bool absolute;
/* If absolute is false, delta time units per quarter note.  If absolute is
   true, delta time units or per second.  */
short division;

/* Chunks and tracks.  */
struct chunk
{
  unsigned char *start;		/* memory image of the MIDI chunk */
  unsigned char *limit;		/* one byte past memory chunk */
  unsigned char *cursor;	/* cursor in memory chunk */
  short track;			/* track number for printing */
  short running_status;		/* running status after last event */
  unsigned tempo;		/* micro-seconds per quarter note */
  unsigned delta_time;		/* delta time value for printing */
  unsigned time_next;		/* time of incoming event in this track */
};
static struct chunk *header;	/* header chunk */
static struct chunk **track_array; /* array of track descriptors */
static unsigned number_of_tracks; /* number of tracks in file */

/* MIDI output file.  */
static int midi_out;

/* Debugging.  */

static int debug;

#define assert(Expr) \
  do {								\
    if (!(Expr))						\
      assert_error (#Expr, __FILE__, __LINE__,			\
	       chunk->cursor - buffer_start);			\
  } while (0)

void
assert_error (const char *message, const char *file,
	      unsigned line, unsigned byte)
{
  fprintf (stderr, "%s:%d: %s[%d] %s\n", file, line, file_name, byte, message);
}

/* File input and output.  */

/*------------------------------------------------------------------------.
| This routine will attempt to swallow a whole file name FILE_NAME into a |
| contiguous region of memory and return a description of it into BLOCK.  |
| Standard input is assumed whenever FILE_NAME is NULL, empty or "-".	  |
| 									  |
| Previously, in some cases, white space compression was attempted while  |
| inputting text.  This was defeating some regexps like default end of	  |
| sentence, which checks for two consecutive spaces.  If white space	  |
| compression is ever reinstated, it should be in output routines.	  |
`------------------------------------------------------------------------*/

static void
swallow_file_in_memory (const char *file_name, char **start, char **end)
{
  int file_handle;		/* file descriptor number */
  struct stat stat_block;	/* stat block for file */
  size_t allocated_length;	/* allocated length of memory buffer */
  size_t used_length;		/* used length in memory buffer */
  int read_length;		/* number of character gotten on last read */

  /* As special cases, a file name which is NULL or "-" indicates standard
     input, which is already opened.  In all other cases, open the file from
     its name.  */

  if (!file_name || !*file_name || strcmp (file_name, "-") == 0)
    file_handle = fileno (stdin);
  else
    if ((file_handle = open (file_name, O_RDONLY)) < 0)
      error (EXIT_FAILURE, errno, file_name);

  /* If the file is a plain, regular file, allocate the memory buffer all at
     once and swallow the file in one blow.  In other cases, read the file
     repeatedly in smaller chunks until we have it all, reallocating memory
     once in a while, as we go.  */

  if (fstat (file_handle, &stat_block) < 0)
    error (EXIT_FAILURE, errno, file_name);

#if !MSDOS

  /* The following code is verboten on MSDOS, because we cannot predict the
     memory size from file size, due to end of line conversions.  */

  if (S_ISREG (stat_block.st_mode))
    {
      *start = (char *) xmalloc ((size_t) stat_block.st_size);

      if (read (file_handle, *start, (size_t) stat_block.st_size)
	  != stat_block.st_size)
	error (EXIT_FAILURE, errno, file_name);

      *end = *start + stat_block.st_size;
    }
  else

#endif /* !MSDOS */

    {
      *start = (char *) xmalloc ((size_t) 1 << SWALLOW_REALLOC_LOG);
      used_length = 0;
      allocated_length = (1 << SWALLOW_REALLOC_LOG);

      while (read_length = read (file_handle,
				 *start + used_length,
				 allocated_length - used_length),
	     read_length > 0)
	{
	  used_length += read_length;
	  if (used_length == allocated_length)
	    {
	      allocated_length += (1 << SWALLOW_REALLOC_LOG);
	      *start = (char *) xrealloc (*start, allocated_length);
	    }
	}

      if (read_length < 0)
	error (EXIT_FAILURE, errno, file_name);

      *end = *start + used_length;
    }

  /* Close the file, but only if it was not the standard input.  */

  if (file_handle != fileno (stdin))
    close (file_handle);
}

/* Analysis of MIDI image.  */

static inline int
parse_int7 (struct chunk *chunk)
{
  assert (chunk->cursor < chunk->limit);
  assert ((*chunk->cursor & 0x80) == 0);
  return *chunk->cursor++;
}

static inline int
parse_int14 (struct chunk *chunk)
{
  int value = 0;
  int counter;

  assert (chunk->cursor + 2 <= chunk->limit);
  for (counter = 0; counter < 2; counter++)
    {
      assert ((*chunk->cursor & 0x80) == 0);
      value = (value << 7) | *chunk->cursor++;
    }

  return value;
}

static inline int
parse_intfix (struct chunk *chunk, int length)
{
  int value = 0;

  assert (chunk->cursor + length <= chunk->limit);
  while (length > 0)
    {
      value = (value << 8) | *chunk->cursor++;
      length--;
    }

  return value;
}

static inline int
parse_intvar (struct chunk *chunk)
{
  int value;

  assert (chunk->cursor < chunk->limit);
  if (*chunk->cursor & 0x80)
    {
      value = *chunk->cursor++ & 0x7f;
      assert (chunk->cursor < chunk->limit);
      while (*chunk->cursor & 0x80)
	{
	  value = (value << 7) | (*chunk->cursor++ & 0x7f);
	  assert (chunk->cursor < chunk->limit);
	}
      return (value << 7) | *chunk->cursor++;
    }
  else
    return *chunk->cursor++;
}

static void
parse_bytes (struct chunk *chunk, int length, int dump, const char *message)
{
  assert (chunk->cursor + length <= chunk->limit);
  if (dump)
    {
      if (debug & DUMP_DELTAS)
	printf ("%4d  ", chunk->delta_time);
      printf ("trk%-2d %s:", chunk->track, message);
      while (length > 0)
	{
	  printf (" %02x", *chunk->cursor);
	  chunk->cursor++;
	  length--;
	}
      putchar ('\n');
    }
  else
    chunk->cursor += length;
}

static void
parse_text (struct chunk *chunk, int length, const char *message)
{
  assert (chunk->cursor + length <= chunk->limit);
  if (debug & DUMP_METAS)
    {
      if (debug & DUMP_DELTAS)
	printf ("%4d  ", chunk->delta_time);
      printf ("trk%-2d %s: ", chunk->track, message);
      while (length > 0)
	{
	  putchar (*chunk->cursor);
	  chunk->cursor++;
	  length--;
	}
      printf ("\n");
    }
  else
    chunk->cursor += length;
}

static void
rewind_track (struct chunk *chunk)
{
  unsigned clock_next;

  chunk->cursor = chunk->start + 8;
  /* Default to piano on channel 1.  */
  chunk->running_status = 0;
  /* 0.5 sec. per beat == 120 beats per min. when factor is 100.  */
  chunk->tempo = 5000 * speed_factor;
  chunk->delta_time = parse_intvar (chunk);
  chunk->time_next = chunk->delta_time;
}

static void
advance_track (struct chunk *chunk, bool perform)
{
  int channel;
  int pitch;
  int velocity;
  int pressure;
  int parameter;
  int setting;
  int program;
  int wheel;
  int event;
  int length;
  char string[20];
  unsigned char *midi_out_cursor = chunk->cursor;

  /* Parse one event, which is a MIDI event, a sysex event or a
     meta-event.  MIDI events cover voice messages only, as system
     messages and real time messages do not occur in MIDI files.  */

  assert (chunk->cursor < chunk->limit);
  if (*chunk->cursor & 0x80)
    {
      if (channel_zero && (*chunk->cursor & 0xf0) != 0xf0)
	*chunk->cursor &= 0xf0;
      event = *chunk->cursor++;
      if (event < 0xf0)
	chunk->running_status = event;
    }
  else
    {
      assert (chunk->running_status >= 0);
      event = chunk->running_status;
      if (perform)
	{
	  char running_status = chunk->running_status;
	  write (midi_out, &running_status, 1);
	}
    }

  switch (event & 0xf0)
    {
    case 0x80:		/* MIDI event: note off */
      channel = chunk->running_status & 0x0f;
      pitch = parse_int7 (chunk);
      velocity = parse_int7 (chunk);
      if (debug & DUMP_NOTES)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  printf ("trk%-2d ch%-2d off %d %d\n", chunk->track, channel,
		  pitch, velocity);
	}
      break;

    case 0x90:		/* MIDI event: note on */
      channel = chunk->running_status & 0x0f;
      pitch = parse_int7 (chunk);
      velocity = parse_int7 (chunk);
      if (debug & DUMP_NOTES)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  if (velocity == 0)
	    printf ("trk%-2d ch%-2d off %d\n", chunk->track, channel,
		    pitch);
	  else
	    printf ("trk%-2d ch%-2d on %d %d\n", chunk->track, channel,
		    pitch, velocity);
	}
      if (pitch && channel != drum_channel
	  && pitch + transpose > 0 && pitch + transpose < 128)
	chunk->cursor[-2] += transpose;
      break;

    case 0xa0:		/* MIDI event: key pressure */
      channel = chunk->running_status & 0x0f;
      pitch = parse_int7 (chunk);
      pressure = parse_int7 (chunk);
      if (debug & DUMP_EVENTS)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  printf ("trk%-2d ch%-2d key-pressure %d %d\n", chunk->track, channel,
		  pitch, pressure);
	}
      break;

    case 0xb0:		/* MIDI event: parameter */
      channel = chunk->running_status & 0x0f;
      parameter = parse_int7 (chunk);
      setting = parse_int7 (chunk);
      if (debug & DUMP_EVENTS)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  printf ("trk%-2d ch%-2d parameter %d %d\n", chunk->track, channel,
		  parameter, setting);
	}
      break;

    case 0xc0:		/* MIDI event: program */
      if (freeze_channel)
	perform = false;
      else
	{
	  channel = chunk->running_status & 0x0f;
	  program = parse_int7 (chunk);
	  if (debug & DUMP_EVENTS)
	    {
	      if (debug & DUMP_DELTAS)
		printf ("%4d  ", chunk->delta_time);
	      printf ("trk%-2d ch%-2d program %d\n", chunk->track, channel,
		      program);
	    }
	}
      break;

    case 0xd0:		/* MIDI event: channel pressure */
      channel = chunk->running_status & 0x0f;
      pressure = parse_int7 (chunk);
      if (debug & DUMP_EVENTS)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  printf ("trk%-2d ch%-2d channel-pressure %d\n", chunk->track, channel,
		  pressure);
	}
      break;

    case 0xe0:		/* MIDI event: pitch wheel */
      channel = chunk->running_status & 0x0f;
      wheel = parse_int14 (chunk) - 0x2000;
      if (debug & DUMP_EVENTS)
	{
	  if (debug & DUMP_DELTAS)
	    printf ("%4d  ", chunk->delta_time);
	  printf ("trk%-2d ch%-2d pitch-wheel %d\n", chunk->track, channel,
		  wheel);
	}
      break;

    case 0xf0:
      chunk->running_status = -1;
      switch (event)
	{
	case 0xf0:	/* sysex event */
	  parse_bytes (chunk, parse_intvar (chunk),
		       debug & DUMP_EVENTS, "sysex");
	  break;

	case 0xf7:	/* sysex event (continuation) */
	  parse_bytes (chunk, parse_intvar (chunk),
		       debug & DUMP_EVENTS, "sysex-cont");
	  break;

	case 0xff:	/* meta-event */
	  event = parse_int7 (chunk);
	  length = parse_intvar (chunk);
	  switch (event)
	    {
	    case 0x01:
	      parse_text (chunk, length, "Text");
	      break;

	    case 0x02:
	      parse_text (chunk, length, "Copyright");
	      break;

	    case 0x03:
	      parse_text (chunk, length, "Sequence/Track");
	      break;

	    case 0x04:
	      parse_text (chunk, length, "Instrument");
	      break;

	    case 0x05:
	      parse_text (chunk, length, "Lyric");
	      break;

	    case 0x06:
	      parse_text (chunk, length, "Marker");
	      break;

	    case 0x07:
	      parse_text (chunk, length, "Cue");
	      break;

	    case 0x2f:
	      assert (length == 0);
	      if (debug & DUMP_METAS)
		{
		  if (debug & DUMP_DELTAS)
		    printf ("%4d  ", chunk->delta_time);
		  printf ("trk%-2d End of Track\n", chunk->track);
		}
	      break;

	    case 0x51:
	      assert (length == 3);
	      {
		int tempo = parse_intfix (chunk, 3);
		int counter;

		if (debug & DUMP_METAS)
		  {
		    if (debug & DUMP_DELTAS)
		      printf ("%4d  ", chunk->delta_time);
		    printf ("trk%-2d Set Tempo %d\n", chunk->track, tempo);
		  }
		if (perform)
		  {
		    tempo = tempo * speed_factor / 100;
		    if (midi_file_format == 1)
		      for (counter = 0; counter < number_of_tracks; counter++)
			track_array[counter]->tempo = tempo;
		    else
		      chunk->tempo = tempo;
		  }
	      }
	      break;

	    case 0x54:
	      parse_bytes (chunk, length,
			   debug & DUMP_METAS, "SMPTE Offset");
	      break;

	    case 0x58:
	      parse_bytes (chunk, length,
			   debug & DUMP_METAS, "Time Signature");
	      break;

	    case 0x59:
	      parse_bytes (chunk, length,
			   debug & DUMP_METAS, "Key Signature");
	      break;

	    case 0x7f:
	      parse_bytes (chunk, length,
			   debug & DUMP_METAS, "Sequencer-Specific");
	      break;

	    default:
	      sprintf (string, "Meta Event %02x", event);
	      parse_bytes (chunk, length,
			   debug & DUMP_METAS, string);
	    }
	  break;

	default:	/* undefined */
	  if (debug & DUMP_EVENTS)
	    {
	      if (debug & DUMP_DELTAS)
		printf ("%4d  ", chunk->delta_time);
	      printf ("trk%-2d Undefined %02x:", chunk->track, event);
	    }
	  while (chunk->cursor < chunk->limit && (*chunk->cursor & 0x80) == 0)
	    {
	      if (debug & DUMP_EVENTS)
		printf (" %02x", *chunk->cursor);
	      chunk->cursor++;
	    }
	}
    }

  /* Play accumulated MIDI output.  */

  if (perform && chunk->running_status >= 0)
    {
      write (midi_out, midi_out_cursor, chunk->cursor - midi_out_cursor);
      midi_out_cursor = chunk->cursor;
    }
}

static struct chunk *
new_chunk (void)
{
  struct chunk *chunk = xmalloc (sizeof (struct chunk));
  unsigned chunk_length;

  chunk->start = buffer_cursor;
  chunk->limit = buffer_limit;
  if (buffer_cursor + 4 > buffer_limit)
    error (EXIT_FAILURE, 0, "Invalid file");
  chunk->cursor = buffer_cursor + 4;
  chunk_length = parse_intfix (chunk, 4);
  buffer_cursor = chunk->cursor + chunk_length;
  chunk->limit = buffer_cursor;

  return chunk;
}

static void
parse_track_image (struct chunk *chunk)
{
  while (chunk->cursor < chunk->limit)
    {
      advance_track (chunk, false);
      if (chunk->cursor < chunk->limit)
	chunk->delta_time = parse_intvar (chunk);
    }
}

static void
parse_midi_image (void)
{
  unsigned counter;
  struct chunk *chunk;

  buffer_cursor = buffer_start;
  chunk = new_chunk ();
  chunk->track = 0;
  header = chunk;

  /* Parse the header chunk.  */

  assert (memcmp (chunk->start, "MThd", 4) == 0);
  assert (chunk->limit == chunk->cursor + 6);
  midi_file_format = parse_intfix (chunk, 2);
  assert (midi_file_format >= 0 && midi_file_format <= 2);
  counter = parse_intfix (chunk, 2);
  track_array = xmalloc (counter * sizeof (struct chunk));
  number_of_tracks = counter;
  division = parse_intfix (chunk, 2);

  printf ("Format %d, division %d\n", midi_file_format, division);
  fflush (stdout);

  /* Find all track chunks.  */

  for (counter = 0; counter < number_of_tracks; counter++)
    {
      chunk = new_chunk ();
      assert (memcmp (chunk->start, "MTrk", 4) == 0);
      chunk->track = counter + 1;
      if (check_mode && (!extract || extract == chunk->track))
	parse_track_image (chunk);
      track_array[counter] = chunk;
    }
  assert (buffer_cursor == buffer_limit);
}

static void
dump_midi_image (const char *name)
{
  int file = creat (name, 0666);

  if (file < 0)
    error (EXIT_FAILURE, errno, name);
  write (file, buffer_start, buffer_limit - buffer_start);
  close (file);
}

static void
perform_tracks (void)
{
  int counter;
  struct timeval zero_timeval;	/* real time reference */
  struct timeval now_timeval;	/* current real time */
  unsigned current_midi_time;	/* MIDI time distance from reference */

  if (midi_out = open ("/dev/midi00", O_WRONLY), midi_out < 0)
    error (EXIT_FAILURE, errno, _("Cannot open /dev/midi00"));

  for (counter = 0; counter < number_of_tracks; counter++)
    if (!extract || extract == counter + 1)
      rewind_track (track_array[counter]);

  if (gettimeofday (&zero_timeval, NULL) < 0)
    error (EXIT_FAILURE, errno, "gettimeofday");
  current_midi_time = 0;

  while (true)
    {
      struct chunk *earliest = NULL;

      for (counter = 0; counter < number_of_tracks; counter++)
	if (!extract || extract == counter + 1)
	  {
	    struct chunk *chunk = track_array[counter];

	    if (chunk->cursor < chunk->limit
		&& (!earliest || chunk->time_next < earliest->time_next))
	      earliest = chunk;
	  }
      if (!earliest)
	break;

      if (current_midi_time < earliest->time_next)
	{
	  /* We should wait.  However, the real time moved as this program
	     burns CPU or has been context switched out by the operating
	     system, and we might have to adjust the wait for such lags.  */

	  if (gettimeofday (&now_timeval, NULL) < 0)
	    error (EXIT_FAILURE, errno, "gettimeofday");
	  if (now_timeval.tv_sec > zero_timeval.tv_sec
	      || (now_timeval.tv_sec == zero_timeval.tv_sec
		  && now_timeval.tv_usec > zero_timeval.tv_usec))
	    {
	      unsigned wanted_usecs
		= (earliest->time_next * earliest->tempo) / division;
	      unsigned real_usecs
		=  ((now_timeval.tv_sec - zero_timeval.tv_sec) * 1000000
		    + (now_timeval.tv_usec - zero_timeval.tv_usec));

	      if (wanted_usecs > real_usecs + 1000)
		msleep ((wanted_usecs - real_usecs) / 1000);
	    }

	  /* For long plays, there is a danger of overflowing microsecond
	     computations.  For example, timing tracks may hold widely spaced
	     events.  So, move theoretical MIDI times backward and real time
	     reference point forward whenever this can be done exactly.  */

	  if (earliest->time_next > division)
	    {
	      int time_leaps = earliest->time_next / division;
	      int time_warp = time_leaps * division;

	      for (counter = 0; counter < number_of_tracks; counter++)
		 if (!extract || extract == counter + 1)
		   track_array[counter]->time_next -= time_warp;
	      zero_timeval.tv_usec += time_leaps * earliest->tempo;
	      zero_timeval.tv_sec += zero_timeval.tv_usec / 1000000;
	      zero_timeval.tv_usec %= 1000000;
	    }

	  /* Maintain theoretical time independently of real time.  */

	  current_midi_time = earliest->time_next;

	  if (debug)
	    fflush (stdout);
	}

      advance_track (earliest, true);
      if (earliest->cursor < earliest->limit)
	{
	  unsigned time_next;

	  earliest->delta_time = parse_intvar (earliest);
	  earliest->time_next = current_midi_time + earliest->delta_time;
	}
    }

  close (midi_out);
}


/* Option decoding and main program.  */

/*------------------------------------------------------.
| Print program identification and options, then exit.  |
`------------------------------------------------------*/

static void
usage (int status)
{
  if (status != EXIT_SUCCESS)
    fprintf (stderr, _("Try `%s --help' for more information.\n"),
	     program_name);
  else
    {
      printf (_("\
Usage: %s [OPTION]... [INPUT]\n"),
	      program_name);
      fputs (_("\
Mandatory arguments to long options are mandatory for short options too.\n\
\n\
  -c, --check            check MIDI file without performing it\n\
  -s, --speed=FACTOR     adjust speed, bigger the slower, default is 100\n\
  -f, --freeze-channel   inhibit all program changes\n\
  -z, --channel-zero     force all notes on channel zero\n\
  -t, --transpose=NUM    number of semi-tones of transposition\n\
  -d, --drum=CHANNEL     drum channel, not to be transposed, default is 9\n\
  -m, --map=IN..OUT      map IN selection into OUT selection\n\
  -D, --debug=BITS       turn on debug bits, default is 8\n\
      --help             display this help and exit\n\
      --version          output version information and exit\n\
\n\
BITS are 1 deltas, 2 MIDI notes, 4 other MIDI events, 8 meta-events.\n\
\n\
With no FILE or if FILE is -, read Standard Input.\n"),
	     stdout);
    }
  exit (status);
}

/*----------------------------------------------------------------------.
| Main program.  Decode ARGC arguments passed through the ARGV array of |
| strings, then launch execution.				        |
`----------------------------------------------------------------------*/

/* Long options equivalences.  */
static const struct option long_options[] =
{
  {"check", no_argument, NULL, 'c'},
  {"channel-zero", no_argument, NULL, 'z'},
  {"debug", required_argument, NULL, 'D'},
  {"extract", required_argument, NULL, 'x'},
  {"freeeze-channel", no_argument, NULL, 'f'},
  {"help", no_argument, &show_help, 1},
  {"drum", required_argument, NULL, 'd'},
  {"map", required_argument, NULL, 'm'},
  {"speed", required_argument, NULL, 's'},
  {"transpose", required_argument, NULL, 't'},
  {"version", no_argument, &show_version, 1},
  {0, 0, 0, 0}
};

int
main (int argc, char *const argv[])
{
  int optchar;			/* argument character */

  /* Decode program options.  */

  program_name = argv[0];
  setlocale (LC_ALL, "");

  while (optchar = getopt_long (argc, argv, "D:cd:fm:s:t:x:z",
				long_options, NULL),
	 optchar != EOF)
    {
      switch (optchar)
	{
	default:
	  usage (EXIT_FAILURE);

	case 0:
	  break;

	case 'D':
	  debug_bits = atoi (optarg);
	  break;

	case 'c':
	  check_mode = true;
	  break;

	case 'd':
	  drum_channel = atoi (optarg);
	  break;

	case 'f':
	  freeze_channel = true;
	  break;

	case 'm':
	  extract = atoi (optarg);
	  break;

	case 's':
	  speed_factor = atoi (optarg);
	  break;

	case 't':
	  transpose = atoi (optarg);
	  break;

	case 'x':
	  break;

	case 'z':
	  channel_zero = true;
	  break;
	}
    }

  /* Process trivial options.  */

  if (show_help)
    usage (EXIT_SUCCESS);

  if (show_version)
    {
      printf ("GNU %s %s\n", PACKAGE, VERSION);
      exit (EXIT_SUCCESS);
    }

  /* Read MIDI file whole into memory.  */

  if (optind == argc)
    {
      file_name = "-";
      swallow_file_in_memory
	(NULL, (char **) &buffer_start, (char **) &buffer_limit);
    }
  else
    {
      file_name = argv[optind++];
      swallow_file_in_memory
	(file_name, (char **) &buffer_start, (char **) &buffer_limit);

      /* Diagnose any other argument as an error.  */
      if (optind < argc)
	usage (EXIT_FAILURE);
    }

  /* Should probably make some option for debugging levels.  */

  if (check_mode)
    {
      debug = debug_bits;
      parse_midi_image ();
    }
  else
    {
      debug = 0;
      parse_midi_image ();
      debug = debug_bits;
      perform_tracks ();
    }

  /* All done.  */

  exit (EXIT_SUCCESS);
}
