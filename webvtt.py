# -*- coding=utf-8 -*-
# TODO LICENSE
"""
A WebVTT Parser
"""
from __future__ import division, unicode_literals

from re import compile as regex
from logging import getLogger

# parser states
METADATA = 1
CUE_OR_NOTE = 2
CUE_TIMINGS = 3
CUE_PAYLOAD = 4
NOTE_PAYLOAD = 5
SKIP = 6

# regexp
MAGIC = regex(r'WEBVTT([ \t]+|$)')
ARROW = regex(r'\s*-->\s*')
NOTE = regex(r'NOTE([ \t]+|$)')
WHITESPACE = regex(r'[ \t]+')

LOG = getLogger(__name__)


class WebVTTParseError(Exception):
    def __init__(self, message, lineno):
        LOG.error("line %s: %s", lineno, message)
        Exception.__init__(self, message)
        self.lineno = lineno

def parse(txt, strict=False):
    """
    TODO docstring
    """
    if not isinstance(txt, unicode):
        if hasattr(txt, "read"):
            txt = txt.read()
        if not isinstance(txt, unicode):
            txt = txt.decode("utf-8")

    LOG.info("parsing in %s mode", ("strict" if strict else "lax"))

    if strict:
        def warn(message, lineno, _lax_only_message=""):
            raise WebVTTParseError(message, lineno)
    else:
        def warn(message, lineno, lax_only_message=""):
            LOG.warn("line %s: %s%s", lineno, message, lax_only_message)

    metadata = {}
    cues = []
    out = {
        "webvtt-head": None,
        "metadata": metadata,
        "cues": cues,
    }

    lines = txt.splitlines()
    if lines:
        firstline = lines.pop(0)
    else:
        firstline = ""
    current_cue = None

    magic = MAGIC.match(firstline)
    if magic:
        out["webvtt-head"] = firstline[magic.end():]
        state = METADATA
    else:
        warn("magic string 'WEBVTT' not found at start", 1,
             ", skipping metadata and looking for cue")
        state = CUE_OR_NOTE

    for lineno, line in enumerate(lines, 2):

        if state == METADATA:
            if not line:
                state = CUE_OR_NOTE
            else:
                elements = line.split(":", 1)
                if len(elements) < 2:
                    warn("ignoring malformed metadata header", lineno)
                else:
                    key, val = elements
                    values = metadata.get(key)
                    if values is None:
                        values = []
                        metadata[key] = values
                    values.append(skip_whitespace(val))
                            
        elif state == CUE_OR_NOTE:
            if not line:
                pass
            else:
                if NOTE.match(line):
                    state = NOTE_PAYLOAD
                    if ARROW.search(line):
                        warn("illegal '-->' in comment", lineno)
                        state = SKIP
                else:
                    elements = ARROW.split(line, 1)
                    if len(elements) == 1:
                        current_cue = { "id": line, "payload": [] }
                        state = CUE_TIMINGS
                    else: # len(elements) == 2:
                        current_cue = { "payload": [] }
                        state = parse_timings(elements, lineno,
                                                 current_cue, warn)
                
        elif state == CUE_TIMINGS:
            elements = ARROW.split(line, 1)
            if len(elements) == 1:
                warn("invalid cue timings line", lineno, ", ignoring cue")
                current_cue = None
                if line:
                    state = SKIP
                else:
                    state = CUE_OR_NOTE
            else: # len(elements) == 2:
                state = parse_timings(elements, lineno, current_cue, warn)
                
        elif state == CUE_PAYLOAD:
            if line:
                current_cue["payload"].append(line)
            else:
                finalize_cue(current_cue, cues)
                current_cue = None
                state = CUE_OR_NOTE
                
        elif state == NOTE_PAYLOAD:
            if line:
                if ARROW.search(line):
                    warn("illegal '-->' in comment", lineno)
                    state = SKIP
            else:
                state = CUE_OR_NOTE

        elif state == SKIP:
            if not line:
                state = CUE_OR_NOTE
        else:
            raise WebVTTParseError("Unrecognized state %s" % state, lineno)

    if current_cue is not None  and  state == CUE_PAYLOAD:
        finalize_cue(current_cue, cues)
        
    return out

def skip_whitespace(txt):
    """
    :param txt: a text
    :return: txt without leading whitespace
    """
    leadingspace = WHITESPACE.match(txt)
    if leadingspace:
        txt = txt[leadingspace.end():]
    return txt

def parse_timings(elements, lineno, current_cue, warn):
    """
    :param elements: a list of 2 elements, representing the components of the
        line after splitting per ARROW
    :param lineno: the number of the current line
    :param current_cue: the object representing the cue being parsed
    :param warn: the warning function

    :return: the new parser state
    """
    # TODO actually parse timings, plus region specification
    timestamp1 , rest = elements
    timestamp1 = current_cue["timestamp1"] \
               = parse_timestamp(skip_whitespace(timestamp1))
    if timestamp1 is None:
        warn("invalid first timestamp", lineno, ", ignoring cue")
        return SKIP

    elements = WHITESPACE.split(rest)
    timestamp2 = current_cue["timestamp2"] = parse_timestamp(elements[0])
    if timestamp2 is None:
        warn("invalid second timestamp", lineno, ", ignoring cue")
        return SKIP
    settings = current_cue["settings"] = {}
    for setting in elements[1:]:
        if ARROW.search(setting):
            warn("illegal '-->' in cue settings", lineno)
        setting_elements = setting.split(":", 2)
        key = setting_elements[0]
        val = setting_elements[1] if len(setting_elements) == 2 else None
        values = settings.get(key)
        if values is None:
            values = []
            settings[key] = values
        values.append(val)
        
    return CUE_PAYLOAD

def parse_timestamp(txt):
    """
    :param txt: a timestamp string
    
    :return: either a list containing [hours, minutes, seconds, fractions]
        or None if txt is an invalid timestamp
    """
    try:
        if txt[-4] != '.':
            return None
        fractions = int(txt[-3:])

        values = txt[:-4].split(":")
        if len(values) > 3:
            return None
        elif len(values) == 1:

            # this is just seconds
            seconds = int(values[0])
            if seconds < 60:
                minutes = 0
            else:
                minutes = seconds // 60
                seconds = seconds % 60
            if minutes < 60:
                hours = 0
            else:
                hours = minutes // 60
                minutes = minutes % 60
                
        else: # 2 <= len(values) <= 3

            if len(values) == 3:
                hours, minutes, seconds = values
                hours = int(hours)
            else: # lent(values) == 2
                minutes, seconds = values
                hours = 0
            minutes = int(minutes)
            seconds = int(seconds)

        return [ hours, minutes, seconds, fractions ]

    except ValueError:
        return None
        
def finalize_cue(current_cue, cues):
    """
    :param current_cue: the object representing the cue being parsed
    :param cue: the list of finalized cues
    """
    payload = "\n".join(current_cue["payload"])
    current_cue["payload"] = payload
    cues.append(current_cue)
