from webvtt import parse

from json import dumps, load as load_json
from os import listdir
from os.path import dirname, join
import sys 

DIR = dirname(__file__)
sys.path.append(dirname(DIR))

def check_file(filename):
    # test filename are structured as inXX.vtt,
    # and result filenames are structured as outXX.json
    resultname = "out%s.json" % (filename[2:-4])
    with open(join(DIR, filename)) as infile:
        got = parse(infile, True)
    with open(join(DIR, resultname)) as outfile:
        exp = load_json(outfile)
    assert got == exp, dumps(got, indent=4)


def test_files():
    for filename in listdir(DIR):
        if filename[:2] == "in" and filename[-4:] == ".vtt":
            yield check_file, filename
