# upon first thought - these shouldn't inherit from Exception
# making them throwable and getting a stacktrace and line number
# just doesn't seem useful here

class DataError:

    def __init__(self, file, message=''):
        self.message = message
        self.file = file

    def __str__(self):
        return ' '.join((self.__class__.__name__, 'in file', self.file, '\n', self.message))
        
class MissingDataError(DataError):

    def __init__(self, file, missing_tags: list[str], message=''):
        self.missing_tags = missing_tags
        self.file = file
        DataError.__init__(self, file, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self),'\n', 
                          'offending tag(s):\n', 
                          ',\n'.join(f'  "{tag}"' for tag in self.missing_tags) ))

class ConflictingDataError(DataError):
    
    def __init__(self, initial_confl: tuple[str, str], conflicting: list[tuple[str, str]], message=''):
        self.initial_confl = initial_confl
        self.conflicting = conflicting
        DataError.__init__(self, self.initial_confl[0], message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self), '\n',
                          str(self.initial_confl),
                          'conflicts with',
                          ', '.join(str(confl) for confl in self.conflicting), '\n'))






