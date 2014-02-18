# -*- coding=utf-8 -*-
# TODO LICENSE
"""
A WebVTT to JSON-LD converter.
"""
from __future__ import unicode_literals

from json import loads
from urlparse import urljoin as irijoin

VTT = "http://champin.net/2014/linkedvtt/onto#"

class WebVTTDLException(Exception):
    pass

def webvtt2jsonld(webvtt, base=None, video=None, context=None, flatten=False):
    """
    :param webvtt: the structure returned by `webvtt.parse`:func:
    :param base: the base IRI (can be overridden by the @video metadata in webvtt)
    :param context: a (list of) context IRI(s)
    :param flatten: whether to flatten named graphs into the default graph
    :return: a JSON-LD compliant structure
    """
    metadata = webvtt["metadata"]
    sys = extract_system_metadata(metadata)

    def genid(cuecount=[0]):
        cuecount[0] += 1
        return "_:cue%s" % cuecount[0]

    base = sys["@base"] or base
    if base is None:
        raise WebVTTDLException("Could not determine base IRI")

    video = sys["@video"] or video
    if video is None:
        raise WebVTTDLException("Could not determine video IRI")
    video = irijoin(base, video)

    if context is None:
        context = []
    elif not isinstance(context, list):
        context = [context]

    cues = []
    out = {
        "@context": [ DEFAULT_CONTEXT ] + context,
        "@id": unicode(base),
        "@type": "VideoMetadataDataset",
        "video": unicode(video),
        "cues": cues,
    }

    for key, val in metadata.items():
        if key[0] != "@":
            out[key] = val

    for cue in webvtt["cues"]:
        cue_id = cue.get("id")
        if cue_id is None:
            cue_id = genid()
        else:
            cue_id = "#id=%s" % cue_id

        ld_cue = {
            "@id": cue_id,
        }

        settings = cue["settings"]
        for key, val in settings.items():
            if key[0] != "@":
                ld_cue[key] = val

        fragment_iri = make_fragment_iri(cue, video)
        payload = cue["payload"]
        try:
            payload = loads(payload)
        except ValueError:
            pass
        if isinstance(payload, dict) and "@id" not in payload:
            payload["@id"] = fragment_iri
            fragment_ld = payload
        else:
            # any other payload is associated to the fragment
            prop = settings.get("@property", ("annotation",))[0]
            fragment_ld = {
                "@id": fragment_iri,
                prop: payload,
            }
        if flatten:
            ld_cue["fragment"] = fragment_ld
        else:
            ld_cue["fragment"] = fragment_iri
            ld_cue["@graph"] = fragment_ld

        cues.append(ld_cue)


    if "@base" in sys:
        out["@context"].insert(0, { "@base": unicode(base) })

    
    out["@context"].extend( irijoin(base, c) for c in sys["@context"] )



    return out

def extract_system_metadata(metadata):
    """
    Extract and check the metadata with special semantics.
    Those are:

    * @base: an single IRI
    * @video: a single IRI (possibly relative)
    * @context: a list of IRIs (possibly relative)

    :param metadata: a dict containing lists of values for each key,
        from which keys can be absent
    :return: a dict containing all the keys, even when empty
    """
    out = {}

    base = metadata.get("@base", (None,))
    if len(base) > 1:
        raise WebVTTDLException("too many @base's in metadata")
    out["@base"] = base[0] 

    video = metadata.get("@video", (None,))
    if len(video) > 1:
        raise WebVTTDLException("too many @video's in metadata")
    out["@video"] = video[0] 

    context = metadata.get("@context", ())
    out["@context"] = context

    return out

def make_fragment_iri(cue, video):
    """
    Make media fragmen IRI from cue JSON objecr and video IRI
    """
    ts1 = cue["timestamp1"]
    assert len(ts1) == 4, ts1
    if ts1[0] == 0:
        ts1 = "%s:%s.%s" % tuple(ts1[1:])
    else:
        ts1 = "%s:%s:%s.%s" % tuple(ts1)
    ts2 = cue["timestamp2"]
    assert len(ts2) == 4, ts1
    if ts2[0] == 0:
        ts2 = "%s:%s.%s" % tuple(ts2[1:])
    else:
        ts2 = "%s:%s:%s.%s" % tuple(ts2)
    # TODO use dedicated settings to extract other media-frag dimensions?
    return "%s#t=%s,%s" % (video, ts1, ts2)


DEFAULT_CONTEXT = {
    "vtt": unicode(VTT),
    "rdf": u"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "owl": u"http://www.w3.org/2002/07/owl#",

    # terms defined by the WebVTT specification
    "Region": "vtt:regionMetadata",
    "vertical": "vtt:vertical",
    "line": "vtt:line",
    "size": "vtt:size",
    "position": "vtt:position",
    "align": "vtt:align",
    "region": "vtt:region",
    # TODO any other metadata or setting defined un WebVTT?
    # ... Should define sub-settings (e.g. region definition?) 

    # terms defined by the WebVTT-LD proposition
    "VideoAnnotationDataset": "vtt:VideoAnnotationDataset",
    "cues": "vtt:hasCue",
    "fragment": "vtt:describesFragment",
    "annotation": "vtt:annotedBy",
}

def main():
    from argparse import ArgumentParser
    from json import dump
    from os import getcwd, path
    from sys import stdin, stdout
    from urllib import pathname2url
    from webvtt import parse
    from pyld.jsonld import JsonLdProcessor

    aparser = ArgumentParser(description="webvtt2rdf converter")
    aparser.add_argument("-i", "--input", type=file, default=stdin)
    aparser.add_argument("-f", "--flatten", action="store_true")
    aparser.add_argument("-v", "--video", type=str,
                         default="http://example.org/video.mp4")
    aparser.add_argument("-F", "--format", choices=["json-ld", "nquads"],
                         default="nquads")
    args = aparser.parse_args()

    if args.input is stdin:
        base = "stdin:"
    else:
        base = "file://" + pathname2url(path.join(getcwd(), args.input.name))
        
    jsonld = webvtt2jsonld(parse(args.input),
                           base,
                           args.video,
                           flatten=args.flatten,
    )
    if args.format == "json-ld":
        dump(jsonld, stdout, indent=4); print "\n"
    else:
        proc = JsonLdProcessor()
        print proc.to_nquads(proc.to_rdf(jsonld, None))

if __name__ == "__main__":
    main()

