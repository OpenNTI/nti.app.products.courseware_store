#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import bz2
import six
import gzip
import mimetypes

def is_true(t):
    result = bool(t and str(t).lower() in ('1', 'y', 'yes', 't', 'true'))
    return result

def get_text(node):
    if node is not None and node.text:
        text = node.text
        text = text.decode("utf-8") if text and isinstance(text, bytes) else text
        return unicode(text) if text else text
    return None

def get_fileobj(source):
    if hasattr(source, 'read'):
        return source
    elif isinstance(source, six.string_types):
        mimetype = mimetypes.guess_type(source)
        if mimetype[1] == 'gzip':
            fileobj = gzip.GzipFile(source)
        elif mimetype[1] == 'bzip2':
            fileobj = bz2.BZ2File(source)
        else:
            fileobj = open(source)
        return fileobj
    return None
