from __future__ import unicode_literals

try:
    xrange
except NameError:
    xrange = range


class Array:

    _MAX_INDEX_LOOKUP_LENGTH = 1000

    def __init__(self, reader, read_all):
        self.reader = reader
        self.begin_pos = self.reader._tell_read_pos()
        self.length = -1

        # For optimizing index queries
        self.last_known_pos = 0
        self.last_known_pos_index = 0
        self.index_lookup = []
        self.index_lookup_multiplier = 1

        if not read_all:
            return

        self._read_all()

    def index(self, value):
        for i, v in enumerate(self):
            if v is value or v == value:
                return i
        raise ValueError

    def count(self, value):
        return sum(1 for v in self if v is value or v == value)

    def to_python(self):
        return self._read_all(to_python=True)

    def __iter__(self, to_python=False):
        self.reader._seek(self.begin_pos)

        if not self.reader._skip_if_next('['):
            raise Exception('Missing "["!')

        self.reader._skip_whitespace()

        if self.reader._skip_if_next(']'):
            return

        while True:
            # Skip or read element
            yield self.reader.read(read_all=True, to_python=to_python)

            # Skip comma or "]" and whitespace around it
            self.reader._skip_whitespace()
            if self.reader._skip_if_next(','):
                self.reader._skip_whitespace()
            elif self.reader._skip_if_next(']'):
                break
            else:
                raise Exception('Expected "," or "]"!')

    def _read_all(self, to_python=False):
        """ Reads and validates all bytes in
        the Array. Also counts its length.

        If 'to_python' is set to true, then returns list.
        """
        if to_python:
            python_list = []
        else:
            python_list = None

        self.length = 0

        for value in self.__iter__(to_python=to_python):
            if to_python:
                python_list.append(value)
            self.length += 1

        return python_list

    def _try_seek(self, index):
        """Find best known position to rewind to requested index."""
        # First try the last known position
        if index >= self.last_known_pos_index:
            seek_index = self.last_known_pos_index
            seek_pos = self.last_known_pos

        # Last known position was too big. If
        # there is no lookup table or index is
        # too small, then start from beginning.
        elif not self.index_lookup or index < self.index_lookup_multiplier:
            seek_index = 0
            seek_pos = 0

        # Try from lookup table
        else:
            lookup_table_index = (index - self.index_lookup_multiplier) / self.index_lookup_multiplier
            # Lookup table index should always be small enough,
            # because if too big indices are requested, then
            # last_known_pos kicks in at the start.
            assert lookup_table_index < len(self.index_lookup)
            seek_index = (lookup_table_index + 1) * self.index_lookup_multiplier
            seek_pos = self.index_lookup[lookup_table_index]

        self.reader._seek(seek_pos)
        return seek_index

    def _update_lookup(self, seek_index):
        """Update lookup variables"""
        if seek_index > self.last_known_pos_index:
            self.last_known_pos_index = seek_index
            self.last_known_pos = self.reader._tell_read_pos()
        if seek_index == (len(self.index_lookup) + 1) * self.index_lookup_multiplier:
            self.index_lookup.append(self.reader._tell_read_pos())
            # If lookup table grows too big, half of its members will be removed
            if len(self.index_lookup) > Array._MAX_INDEX_LOOKUP_LENGTH:
                self.index_lookup = [pos for i, pos in enumerate(self.index_lookup) if i % 2 == 1]
                self.index_lookup_multiplier *= 2

    def __getitem__(self, index):
        # Handle slices and negative indexes
        # TODO: length is not strictly necessary to calculate before for slicing
        if isinstance(index, slice):
            return [self[i] for i in xrange(*index.indices(len(self)))]
        if index < 0:
            index = len(self) + index

        seek_index = self._try_seek(index)

        if seek_index == 0 and not self.reader._skip_if_next('['):
            raise Exception('Missing "["!')
        self.reader._skip_whitespace()

        if self.reader._is_next(']'):
            raise IndexError('Out of range!')

        while True:
            # If this is the requested element, then it doesn't
            # need to be read fully. If not, then its bytes
            # should be skipped, and it needs to be fully read.
            if index == seek_index:
                return self.reader.read(read_all=False)
            else:
                self.reader.read(read_all=True)

            # Skip comma and whitespace around it
            self.reader._skip_whitespace()
            if self.reader._skip_if_next(','):
                self.reader._skip_whitespace()
            elif self.reader._is_next(']'):
                raise IndexError('Out of range!')
            else:
                raise Exception('Expected "," or "]"!')

            seek_index += 1
            self._update_lookup(seek_index)

    def __len__(self):
        if self.length < 0:
            self._read_all()
        return self.length

    def __contains__(self, value):
        return any(v is value or v == value for v in self)
