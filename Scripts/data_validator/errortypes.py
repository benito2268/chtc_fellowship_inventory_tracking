# upon first thought - these shouldn't inherit from Exception
# making them throwable and getting a stacktrace and line number
# just doesn't seem useful here

class DataError:

    def __init__(self, file: str, message=''):
        self.message = message
        self.file = file

    def __str__(self):
        return ' '.join((self.__class__.__name__, 'in file', self.file, '\n', self.message))
        
class MissingDataError(DataError):

    def __init__(self, file: str, missing_tags: list[str], message=''):
        self.missing_tags = missing_tags
        self.file = file
        DataError.__init__(self, file, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self),'\n', 
                          'offending tag(s):\n', 
                          ',\n'.join(f'  "{tag}"' for tag in self.missing_tags) ))

# TODO replace with named tuples to make more clear?
class ConflictingGroupError(DataError):
    
    def __init__(self, initial_group: tuple[str, str], conflicting: list[tuple[str, str]], message=''):
        self.initial_group = initial_group
        self.conflicting = conflicting
        DataError.__init__(self, self.initial_group[0], message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self), '\n',
                          str(self.initial_group),
                          'conflicts with\n',
                          ',\n'.join(str(confl) for confl in self.conflicting), '\n'))






