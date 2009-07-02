/* Déclarations de système.
   Copyright © 1998 Progiciels Bourbeau-Pinard inc.
   François Pinard <pinard@iro.umontreal.ca>, 1998.  */

#if STDC_HEADERS
# include <stdlib.h>
#endif

#ifndef EXIT_SUCCESS
# define EXIT_SUCCESS 0
#endif
#ifndef EXIT_FAILURE
# define EXIT_FAILURE 1
#endif

#if HAVE_STRING_H
# include <string.h>
#else
# include <strings.h>
# ifndef strchr
#  define strchr index
# endif
# ifndef strrchr
#  define strrchr rindex
# endif
#endif

#include <stdio.h>

#include <errno.h>
#ifndef errno
extern int errno;
#endif

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#if STAT_MACROS_BROKEN
# undef S_ISREG
#endif

#if !defined(S_ISREG) && defined(S_IFREG)
# define S_ISREG(Mode) (((Mode) & S_IFMT) == S_IFREG)
#endif

#if HAVE_UNISTD_H
# include <unistd.h>
#endif

#if HAVE_STDBOOL_H
# include <stdbool.h>
#else
typedef enum {false = 0, true = 1} bool;
#endif

#define _(String) String
#if !FIXME
# define setlocale(A, B) /* empty */
#endif

#ifndef PARAMS
# if PROTOTYPES
#  define PARAMS(Args) Args
# else
#  define PARAMS(Args) ()
# endif
#endif

#include "error.h"
#include "getopt.h"
#include "bumpalloc.h"
#include "xalloc.h"

#if WITH_DMALLOC
# define MALLOC_FUNC_CHECK
# include <dmalloc.h>
#endif
