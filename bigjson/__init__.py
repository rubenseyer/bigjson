from .filereader import FileReader


def load(file, read_all=False, to_python=False):
    reader = FileReader(file)
    return reader.read(read_all=read_all, to_python=to_python)
