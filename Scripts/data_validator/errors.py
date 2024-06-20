# upon first thought - these shouldn't inherit from Exception
# making them throwable and getting a stacktrace and line number
# just doesn't seem useful here

class DataError:

    def __init__(self, file, message=''):
        self.message = message
        self.file = file

    def __str__(self):
        return ' '.join((self.__class__.__name__, 'in file', self.file, self.message))
        
class MissingDataError(DataError):

    def __init__(self, file, missing_tags: list, message=''):
        self.missing_tags = missing_tags
        self.file = file
        DataError.__init__(self, file, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self),'\n', 
                          'offending tag(s):\n', 
                          ',\n'.join(f'  "{tag}"' for tag in self.missing_tags) ))

class ConflictingDataError(DataError):
    
    def __init__(self, initial_file, conflicting: list, confl_tag, message=''):
        self.initial_file = initial_file
        self.conflicting = conflicting
        self.confl_tag = confl_tag
        DataError.__init__(self, self.initial_file, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self), '\n', 
                          self.initial_file,
                          'conflicts with',
                          ', '.join(self.conflicting), '\n',
                          'offending tag --',
                          self.confl_tag ))






