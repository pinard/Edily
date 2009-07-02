.. role:: code(strong)
.. role:: file(literal)

=================
The Edily Project
=================

---------------------------------
A MIDI-driven editor for Lilypond
---------------------------------

.. contents::
.. sectnum::

Project description
===================

This package, still in development, is meant to contain a few Python
tools to help editing Lilypond sources within a MIDI environment.

Editor specifications
=====================

Here is the description of the editor to be written.  This is an
attempt, as some areas are still fuzzy, and subject to discussions.

Justification
-------------

Editing normal text on a computer, many people found out that moving the
hands between the keyboard and the mouse slow them down.  Editors often
use keyboard shortcuts for frequently used menu entries, meant for mouse
access.  Users concentrating on the keyboard may recover speed.

Editing a musical score with the help of a MIDI keyboard for note entry,
we loose a lot of time moving hands between the musical and computer
keyboards, not to speak of the mouse.  This project attempts to minimize
the loss by establishing shortcuts right on the MIDI keyboard for most
editing commands.

Now, a MIDI keyboard uses a rather different paradigm than a computer
keyboard.  It would be a big mistake, for example, merely affecting each
individual key of a MIDI keyboard some preset meaning.  Musicians think
in term of sounds, tonality, rythm, and chords.  We should seek a new
paradigm along those lines.

From now on, unless otherwise noted, the term `keyboard` refers to the
MIDI (or musical) keyboard.

Command notation
----------------

The keyboard is either in command mode or in insert mode.  When in
insert mode, notes are echoed over a rug made by a metronome or a
playback of other voices.  When in command mode, the notes making up
commands are not echoed as such, yet each command yields some heard
feedback, either as a musical fragment, either as a pre-recorded human
word or small sentence, or both.

Fingers for both hands are numbered by a single decimal digit, running
from 1 to 5 for the left hand (1 is the left little finger, 5 is the
left thumb) and from 6 to 9 and 0 for the right hand (6 is the right
thumb, 0 is the right little finger).

The actual notes played by the fingers, while entering commands, depend
on the current tonality in the score, and should respect the alterations
for that tonality.  Fingers 1 and 6 should both placed over the tonic of
that tonality, fingers 2 and 7 should be placed on the second degree,
and so on, fingers 5 and 0 should be placed on the fifth degree.  Any
octave of the tonality will do, as long as fingers 1 to 5 use a lower
octave than fingers 6 to 0.

It is not strictly possible to play many notes simultaneously.  Even if
it was possible, the MIDI serialisation would likely make some notes
appear before others.  As commands often use the notion of a chord, a
chord must be precisely defined.  A chord for the left hand starts when
any finger from 1 to 5 presses a note, and contains all notes pressed
by those fingers 1 to 5, until all of fingers 1 to 5 get depressed.
Similarly, a chord for the right hand starts when any finger from 6 to 0
presses a note, and contains all notes pressed by those fingers 6 to 0,
until all of fingers 6 to 0 get depressed.

For example, chord ``134`` could be type in many ways.  The easiest is
merely pressing all of fingers 1, 3 and 4, and depressing them all.  Or
maybe pressing fingers 1 and 3 at once, pressing and releasing finger
4, then releasing fingers 1 and 3.  Or maybe more hairy combinations,
like pressing finger 1, adding finger 4, releasing finger 1 yet holding
down finger 4, pressing and releasing finger 3, even pressing finger 1
again (uselessly) and releasing everything.  Shortly said, a chord for
one hand is all notes between two empties.

A command uses either a chord from the left hand, a chord from the right
hand, or two simultaneous chords, one from each hand.  When a command is
meant either for the left hand only or the right hand only, the other
hand should be empty at the time that command is given, and the command
is complete as soon as all notes are released.  For two simultaneous
chords, it does not matter which one is given first, given that one hand
is not fully released before the other hand chord starts, the command is
complete as soon as one of the hands gets fully released.  To be ultra
precise for the case of a command made up of two simultaneous chords,
as soon as one of the hands gets fully released, that hand's chord is
defined as per above, but the chord for the other hand is defined as
being the set of notes actually pressed when that occurs.

For example, command ``189`` requires a ``1`` chord from the left hand
and a ``89`` chord from the right hand.  One may hold ``1`` down with
the left hand, and play a ``89`` chord with the right hand, then release
``1``.  The command has been issued when ``89`` was released.  Suppose
one wants to command ``189`` three times.  One easy way might be to hold
``89`` down with the right hand, and tap ``1`` three times with the left
hand, only then releasing ``89``.

Commands
themselves use both hands at once.  The left hand chord sets the overall
family of the command, while the right hand chord makes the command in
that family.  When many commands in a row are from the same family, it
is useful to `chain` them, that is, to sit the left hand on its chord,
and while keeping it unreleased, use the right hand for each individual
command.

The command set has been designed so frequent commands are easier to
type.

Command prefixes
----------------

Many commands use an accumulated numerical value which is called a
`prefix` for that command.  Besides numbers, prefixes may also be a few
special values.  When a command uses a prefix, the prefix is reset to
a neutral value once the command is completed.  Each command accepting
a prefix uses a reasonable default value for a prefix, in case none is
given.

Numerical prefixes are made up by special commands using a single finger
at a time.  Each prefix command builds up part of a decimal number.

  ===============   ==========================================================
  ``1.... .....``   Add digit 1 to decimal prefix
  ``.2... .....``   Add digit 2 to decimal prefix
  ``..3.. .....``   Add digit 3 to decimal prefix
  ``...4. .....``   Add digit 4 to decimal prefix
  ``....5 .....``   Add digit 5 to decimal prefix
  ``..... 6....``   Add digit 6 to decimal prefix
  ``..... .7...``   Add digit 7 to decimal prefix
  ``..... ..8..``   Add digit 8 to decimal prefix
  ``..... ...9.``   Add digit 9 to decimal prefix
  ``..... ....0``   Add digit 0 to decimal prefix
  ===============   ==========================================================

In case there is a numerical entry in the prefix, it can be reset by
executing the command setting the tonality.

Positioning commands
--------------------

The editor holds the notion of a cursor, which is a position in the
score.  One command combines sound fragments to tell the cursor
position, expressed as bar, beat and note.

  ===============   ==========================================================
  ``1.... ..8..``   Cursor position
  ===============   ==========================================================

Positioning commands use the right middle finger (8) to represent the
neutral direction, the fingers left of that middle finger indicate a
backward motion, the fingers right of that middle finger indicate a
forward motion.  On the average, when the fingers are further from the
middle finger, the motion is larger.

  ===============   ==========================================================
  ``1.... .78..``   One note backward
  ``1.... ..89.``   One note forward
  ``1.... .7...``   One beat backward
  ``1.... ...9.``   One beat forward
  ``1.... 6....``   One bar backward
  ``1.... ....0``   One bar forward
  ``1.... 6.8..``   Jump to preceding mark
  ``1.... ..8.0``   Jump to following mark
  ``1.... 678..``   Jump to start of score
  ``1.... ..890``   Jump to end of score
  ===============   ==========================================================

For positioning commands, the prefix is used as a multiplicative factor,
as if the command has been given that many times.

Each positioning command gives, as feedback, the current note, the
current beat or the current bar, depending on the command.  For jumping
commands, we hear notes from the current position to the end of the bar.
The feedback is interrupted as soon as another command is received.

Playback commands
-----------------

Playback commands use the same family as positionning commands, to ease
chaining them all.  Symmetrical combinations of the positioning commands
ask for playback of musical fragments.

  ===============   ==========================================================
  ``1.... .789.``   Play note
  ``1.... .7.9.``   Play beat
  ``1.... 6...0``   Play bar
  ``1.... 6.8.0``   Play between enclosing marks
  ``1.... 67890``   Play everything
  ===============   ==========================================================

For playback commands, a prefix multiplicatively extends the span of
what is playing back.

The playback is interrupted as soon as another command is received.

Recording commands
------------------

Nous pourrions attribuer ``2``, disons, à la famille des commandes
pour l'entrée de fragments musicaux.  En tenant ``2`` enfoncé, on
pourrait frapper ``6`` à répétition pour fixer la vitesse et la
phase du métronome, en faisant une moyenne sur les quatre derniers
``6``, disons.  Frapper sur ``6`` une seule fois démarre le métronome
précédent.  Pour Lorsque ``2`` est relâché, l'enregistrement
est presque prêt, il manque simplement le "délimiteur", qui
est une note qui ne fera pas partie métronome, en faisant une
moyenne sur les quatre derniers ``6``, disons.  Frapper sur ``6``
une seule fois démarre le métronome précédent.  Pour Lorsque
``2`` est relâché, l'enregistrement est presque prêt, il manque
simplement le "délimiteur", qui est une note qui ne fera pas partie de
l'enregistrement, et qui ne fait pas partie de ``1`` à ``5`` ni ``6``
à ``0``.  Une fois le délimiteur frappé, l'enregistrement commence
au début de la mesure suivante, et se poursuit jusqu'à ce que le
délimiteur soit frappé à nouveau, ce qui arrête aussi le métronome.
Le résultat de l'enregistrement pourrait être fusionné avec le
contenu courant, en présumant que nous avons déjà des commandes
pour remettre au silence ou insérer de l'espace.  Sinon, l'insertion
pourrait être déplaçante.  Tout ça n'est pas bien réfléchi, je
cherche juste à partager l'intuition d'une idée pour l'instant.
Pour toutes ces modalités, il reste une foule de possibilités non
exploitées à la main droite, je ne crois pas que nous manquions
d'espace pour les commandes.

Voice control commands
----------------------

La touche ``3`` pourrait être attribuée au contrôle des voix.  Quelles
voix sont muettes, quelles voix sont parlantes, pendant la reproduction
des fragments, y compris ceux qui accompagnent le métronome durant
l'enregistrement.  Quelle voix est l'objet des prochains enregistrements
(j'ai présumé que l'on n'enregistre qu'une voix à la fois).  On pourrait
aussi garder de l'espace de commandes pour la fusion des voix, la
séparation des accords en voix distinctes, et ces choses, pour plus
tard.

Modification commands
---------------------

La touche ``4`` servirait à l'édition détaillée.  L'édition de la
hauteur d'une note pourrait probablement être un cas particulier de
la transposition, appliquée à une seule note, et donc déjà couvert.
Par défaut, ``4`` seul serait un éditeur de durée, avec la main droite
indiquant si l'on doit augmenter ou diminuer la durée, déplacer le
départ de la note vers la gauche ou vers la droite, ajouter ou enlever
un point après la note, et peut-être, s'il reste de la place pour ces
commandes, les marques pour staccato, pizzicato, portamento, point
d'orgue. ``4`` possiblement combiné à d'autres touches ``g*`` pourrait
permettre à la main droite de choisir, peut-être avec l'aide de menus
déroulants parlés, parmi la panoplie de toutes les marques disponibles.
Une combinaison ``4+g*`` serait réservée à l'ornementation, et l'on
"dessinerait" alors l'ornementation avec la main droite, en faisant une
appogiature, un mordant, un mordant descendant, un trille commençant par
le haut, par le bas, etc.  Peut-être!

Parameter commands
------------------

La touche ``5``, seule ou combinée, serait réservée à tous les
méta-phénomènes d'édition.  Par exemple, pour déterminer les paramètres
globaux de la partition comme le nombre de temps d'une mesure, l'armure
de la clé (et possiblement la tonalité et le mode ancien aussi), et
d'autres choix généraux qui pourraient affecter le reste de l'édition.
J'aurais tendance à garder ``5`` seule (donc, le pouce de la main gauche
sans autre doigt de la main gauche) pour un système d'abréviation et de
macro-touches, où l'on pourrait définir diverses séquences, incluant ou
excluant des fragments musicaux.  Il faudrait que, dans le cas le plus
J'aurais tendance à garder ``5`` seule (donc, le pouce de la main gauche
sans autre doigt de la main gauche) pour un système d'abréviation et de
macro-touches, où l'on pourrait définir diverses séquences, incluant ou
excluant des fragments musicaux.  Il faudrait que, dans le cas le plus
simple, ``+5-5`` appelle le dernier macro défini, ou peut-être encore
plus utilement, répète la toute dernière modification quelle qu'elle
ait été.

Searching commands
------------------

Il serait probablement utile que ``+1+5`` soit utilisable pour
"fouiller" la partition à la recherche d'un fragment mélodique, ou
rythmique, ou les deux, transposé ou pas.  Ça serait souvent bien plus
simple que de passer par la partition et des numéros de mesure.

Open problems
=============

Il faudrait des commandes pour placer des marques ou les enlever,
bien sûr, l'identification de la marque serait obtenue d'un préfixe
numérique.  Peut-être que ces commandes, ainsi que toutes les commandes
reliées à des déplacements, utilisent des multi-touches à la main
gauche, mais dont ``1`` fait toujours partie.  (Par exemple, `éliminer`
ou `couper`, `coller`, `transposer`, etc.).  En passant, il faut la
modalité d'éliminer en remettant à blanc (au silence) sans déplacer la
suite des notes, aussi bien qu'une élimination déplaçante.

Tu devines sûrement que de spécifier le détail de la façon dont tout
ça doit fonctionner, c'est-à-dire aller bien plus loin que l'esquisse
rapide que j'ai faite dans ce message, est un assez gros travail en soi.
Une implantation devra suivre cette spécification, mais surtout, la
spécification devra être affinée et épurée par l'usage et l'expérience,
afin d'alléger les opérations les plus fréquentes.  Tout doit être assez
pleinement configurable par l'utilisateur, bien sûr, mais un peu comme
Emacs n'est pas tellement changé au niveau des fonctions de base, nous
avons intérêt à offrir une base convenablement songée et acceptable, si
nous voulons éviter une forte confusion par l'effet de la rédéfinition
complète des commandes, dans diverses directions, par des usagers qui
réfléchissent plus loin que nous le faisons.

Il y a aussi une mer de questions non résolues, et probablement non
encore posées.  Par exemple, une parmi bien d'autres, avec quel
dynamisme l'édition au clavier MIDI se répercute immédiatement dans
l'apparence de la partition Lilypond en train d'être éditée, et comment
on peut combiner efficacement une édition utilisant plus ou moins
simultanément les deux claviers.  Certaines questions et problèmes
risquent d'être difficiles, alors il faut aborder tout ça avec courage.

.. Historical notes
.. ================
