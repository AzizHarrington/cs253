import re
import random
import string
import hashlib

### Unit 2 functions ###

### Validation ###

months = ['January',
          'February',
          'March',
          'April',
          'May',
          'June',
          'July',
          'August',
          'September',
          'October',
          'November',
          'December']
          
def valid_month(month):
    for entry in months:
        if month.lower()[:3] == entry.lower()[:3]:
            return entry
    else:
        return None

def valid_day(day):
    if day and day.isdigit():
        if int(day) in range(1, 32):
            return int(day)
        else:
            return None

def valid_year(year):
    if year and year.isdigit():
        year = int(year)
        if year in range(1900, 2021):
            return year

### html escaping ###
#using jinja's auto escape instead.

# symbols = {'>':'&gt;', '<':'&lt;', '"':'&quot;', '&':'&amp;'}

# def escape_html(s):
#     return s.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;').replace('"', '&quot;')


### ROT13 ###

alphabet = {'a': 'n', 'A': 'N',
            'b': 'o', 'B': 'O',
            'c': 'p', 'C': 'P',
            'd': 'q', 'D': 'Q',
            'e': 'r', 'E': 'R',
            'f': 's', 'F': 'S',
            'g': 't', 'G': 'T',
            'h': 'u', 'H': 'U',
            'i': 'v', 'I': 'V',
            'j': 'w', 'J': 'W',
            'k': 'x', 'K': 'X',
            'l': 'y', 'L': 'Y',
            'm': 'z', 'M': 'Z',
            'n': 'a', 'N': 'A',
            'o': 'b', 'O': 'B',
            'p': 'c', 'P': 'C',
            'q': 'd', 'Q': 'D',
            'r': 'e', 'R': 'E',
            's': 'f', 'S': 'F',
            't': 'g', 'T': 'G',
            'u': 'h', 'U': 'H',
            'v': 'i', 'V': 'I',
            'w': 'j', 'W': 'J',
            'x': 'k', 'X': 'K',
            'y': 'l', 'Y': 'L',
            'z': 'm', 'Z': 'M'}

def rot13(some_string):
    result = ''
    for char in some_string:
        if char in alphabet:
            result += alphabet[char]
        else:
            result += char
    return result


### Username, Password, and Email checks ###

def valid_username(username):
    valid = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return valid.match(username)

def valid_password(password):
    valid = re.compile(r"^.{3,20}$")
    return valid.match(password)

def valid_email(email):
    valid = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
    return not email or valid.match(email)


### Hash cookies for password and username ###

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    hashbrowns = hashlib.sha256(name + pw + salt).hexdigest()
    return [hashbrowns, salt]

def valid_pw(name, pw, h):
    salt = h[1]
    hashbrowns = h[0]
    return hashlib.sha256(name + pw + salt).hexdigest() == hashbrowns