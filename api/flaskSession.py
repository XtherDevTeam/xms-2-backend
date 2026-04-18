import os
import codecs
import cgi
import jinja2
from base64 import b64decode
from itsdangerous import base64_decode
import zlib
import json
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, JsonLexer
import uuid
from werkzeug.http import parse_date
from flask import Markup

env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))

def source():
    """Return this script's own source code."""
    me = os.path.join(os.path.abspath(os.path.dirname(__file__)), __file__)
    fh = codecs.open(me, "r", "utf-8")
    code = fh.read().split("\n")[2:]
    fh.close()
    return "\n".join(code)


def decode(cookie):
    """Decode a Flask cookie."""
    try:
        compressed = False
        payload = cookie

        if payload.startswith('.'):
            compressed = True
            payload = payload[1:]

        data = payload.split(".")[0]

        data = base64_decode(data)
        if compressed:
            data = zlib.decompress(data)

        return data.decode("utf-8")
    except Exception as e:
        return "[Decoding error: are you sure this was a Flask session cookie? {}]".format(e)


def flask_loads(value):
    """Flask uses a custom JSON serializer so they can encode other data types.
    This code is based on theirs, but we cast everything to strings because we
    don't need them to survive a roundtrip if we're just decoding them."""
    def object_hook(obj):
        if len(obj) != 1:
            return obj
        the_key, the_value = next(obj.iteritems())
        if the_key == ' t':
            return str(tuple(the_value))
        elif the_key == ' u':
            return str(uuid.UUID(the_value))
        elif the_key == ' b':
            return str(b64decode(the_value))
        elif the_key == ' m':
            return str(Markup(the_value))
        elif the_key == ' d':
            return str(parse_date(the_value))
        return obj
    return json.loads(value, object_hook=object_hook)