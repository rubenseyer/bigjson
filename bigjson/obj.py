from __future__ import unicode_literals
from collections import OrderedDict

try:
    basestring
except NameError:
    basestring = str


class Object:

    _GET_METHOD_RAISE_EXCEPTION = 0
    _GET_METHOD_RETURN_DEFAULT = 1
    _GET_METHOD_RETURN_BOOLEAN = 2

    _MAX_KEY_LOOKUP_LENGTH = 512

    def __init__(self, reader, read_all):
        self.reader = reader
        self.begin_pos = self.reader._tell_read_pos()
        self.length = -1

        # For optimizing _get using an LRU cache
        self.key_lookup = OrderedDict()

        if not read_all:
            return

        self._read_all()

    def keys(self):
        return [keyvalue[0] for keyvalue in self.iteritems()]

    def values(self):
        return [keyvalue[1] for keyvalue in self.iteritems()]

    def items(self):
        return [keyvalue for keyvalue in self.iteritems()]

    def iteritems(self, to_python=False, yield_offsets=False):
        self.reader._seek(self.begin_pos)

        if not self.reader._skip_if_next('{'):
            raise Exception('Missing "{"!')

        self.reader._skip_whitespace()

        if self.reader._skip_if_next('}'):
            return

        while True:
            # Read key. Reading all is not required, because strings
            # are read fully anyway, and if it is not string, then
            # there is an error and reading can be canceled.
            offset = self.reader._tell_read_pos()
            key = self.reader.read(read_all=False)
            if not isinstance(key, basestring):
                raise Exception('Invalid key type in JSON object!')

            # Skip colon and whitespace around it
            self.reader._skip_whitespace()
            if not self.reader._skip_if_next(':'):
                raise Exception('Missing ":"!')
            self.reader._skip_whitespace()

            # Read value
            value = self.reader.read(read_all=True, to_python=to_python)

            if yield_offsets:
                yield (key, value, offset)
            else:
                yield (key, value)

            # Read comma or "}" and whitespace around it.
            self.reader._skip_whitespace()
            if self.reader._skip_if_next(','):
                self.reader._skip_whitespace()
            elif self.reader._skip_if_next('}'):
                break
            else:
                raise Exception('Expected "," or "}"!')

    def get(self, key, default=None):
        return self._get(key, default, Object._GET_METHOD_RETURN_DEFAULT)

    def to_python(self):
        return self._read_all(to_python=True)

    def populate_lookup(self):
        self._read_all(populate_lookup=True)

    def _read_all(self, to_python=False, populate_lookup=False):
        """ Reads and validates all bytes in
        the Object. Also counts its length.

        :param to_python: whether to return a dict
        :param populate_lookup: whether to fill the internal key lookup table
        """
        if to_python:
            python_dict = {}
        else:
            python_dict = None

        self.length = 0

        for key, value, offset in self.iteritems(to_python=to_python, yield_offsets=True):
            if to_python:
                python_dict[key] = value
            if populate_lookup and len(self.key_lookup) < Object._MAX_KEY_LOOKUP_LENGTH:
                self.key_lookup[key] = offset
            self.length += 1

        return python_dict

    def __contains__(self, key):
        return self._get(key, None, Object._GET_METHOD_RETURN_BOOLEAN)

    def __getitem__(self, key):
        return self._get(key, None, Object._GET_METHOD_RAISE_EXCEPTION)

    def _get(self, key, default, method):
        if not isinstance(key, basestring):
            raise TypeError('Key must be string!')

        if key not in self.key_lookup:
            # Rewind to requested element from the beginning
            self.reader._seek(self.begin_pos)
            if not self.reader._skip_if_next('{'):
                raise Exception('Missing "{"!')
            self.reader._skip_whitespace()
        else:
            # Seek to cached key position
            self.reader._seek(self.key_lookup[key])

        if self.reader._is_next('}'):
            if method == Object._GET_METHOD_RAISE_EXCEPTION:
                raise KeyError(key)
            elif method == Object._GET_METHOD_RETURN_DEFAULT:
                return None
            else:
                return False

        while True:
            seek_pos = self.reader._tell_read_pos()
            key2 = self.reader.read(read_all=False)
            if not isinstance(key2, basestring):
                raise Exception('Invalid key type in JSON object!')

            # Read colon
            self.reader._skip_whitespace()
            if not self.reader._skip_if_next(':'):
                raise Exception('Missing ":"!')
            self.reader._skip_whitespace()

            # Cache passed keys in the lookup table
            if key2 not in self.key_lookup:
                if len(self.key_lookup) >= Object._MAX_KEY_LOOKUP_LENGTH:
                    # Drop first (oldest) entry
                    self.key_lookup.popitem(False)
                self.key_lookup[key2] = seek_pos

            # If this is the requested value, then it doesn't
            # need to be read fully. If not, then its bytes
            # should be skipped, and it needs to be fully read.
            if key2 == key:
                # Move this key last in the lookup table so it survives longer
                self.key_lookup.move_to_end(key2)

                if method == Object._GET_METHOD_RETURN_BOOLEAN:
                    return True
                else:
                    return self.reader.read(read_all=False)
            else:
                self.reader.read(read_all=True)

            # Skip comma and whitespace around it
            self.reader._skip_whitespace()
            if self.reader._skip_if_next(','):
                self.reader._skip_whitespace()
            elif self.reader._is_next('}'):
                if method == Object._GET_METHOD_RAISE_EXCEPTION:
                    raise KeyError(key)
                elif method == Object._GET_METHOD_RETURN_DEFAULT:
                    return None
                else:
                    return False
            else:
                raise Exception('Expected "," or "}"!')

    def __len__(self):
        if self.length < 0:
            self._read_all()
        return self.length

    def __iter__(self):
        return (keyvalue[0] for keyvalue in self.iteritems())
