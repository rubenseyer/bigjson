bigjson
=======

Python library that reads JSON files of any size.

The magic is in the Array and Object types.
They load stuff from the file only when necessary.

Fork differences
----------------
 * Compatible with (recent versions of) both Python 2 and 3.
 * Support for equivalent standard library methods on immutable dict/list
 * Support slicing and negative indexes on Array (performance penalty when reading in reverse)

Example
-------

The file size in this example is 78 GB.

```python
import bigjson

with open('wikidata-latest-all.json', 'rb') as f:
    j = bigjson.load(f)
    element = j[4]
    print(element['type'])
    print(element['id'])
```
