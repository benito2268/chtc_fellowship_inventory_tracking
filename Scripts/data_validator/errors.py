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

    def __init__(self, file, missing_tag, message=''):
        self.missing_tag = missing_tag
        self.file = file
        DataError.__init__(self, file, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self),'\n', 
                          'offending tag:', 
                          self.missing_tag ))

class ConflictingDataError(DataError):
    
    def __init__(self, initial_file, conflicting: list, confl_tag, message=''):
        self.conflicting = conflicting
        self.confl_tag = confl_tag
        DataError.__init__(self, file1, message)

    def __str__(self):
        return ' '.join(( DataError.__str__(self), '\n', 
                          self.file1,
                          'conflicts with',
                          ' '.join(self.conflicting), '\n',
                          'offending tag:',
                          self.confl_tag ))






