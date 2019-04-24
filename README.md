bigjson
=======

Python library that reads JSON files of any size.
This fork is compatible with (recent versions of) both Python 2 and 3.

The magic is in the Array and Object types.
They load stuff from the file only when necessary.


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
