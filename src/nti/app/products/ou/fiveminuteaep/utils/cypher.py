#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import base64

from Crypto.Cipher import XOR

from . import get_uid

class Encryption(object):

	def make_ciphertext(self, passphrase, plaintext):
		cipher = XOR.new(passphrase)
		result = base64.b64encode(cipher.encrypt(plaintext))
		return result

	def get_plaintext(self, passphrase, ciphertext):
		cipher = XOR.new(passphrase)
		return cipher.decrypt(base64.b64decode(ciphertext))

def create_token(user, pidm, crn, term_code, return_url, timestamp=None):
	passphrase = unicode(get_uid(user))
	username = user.username.lower()
	timestamp = time.time() if timestamp is None else timestamp
	tokens = map(str, (username, pidm, crn, term_code, return_url, timestamp))
	plaintext = "\t".join(tokens)
	ciphertext = Encryption().make_ciphertext(passphrase, plaintext)
	return ciphertext

def get_plaintext(user, ciphertext):
	passphrase = unicode(get_uid(user))
	plaintext = Encryption().get_plaintext(passphrase, ciphertext)
	return plaintext
