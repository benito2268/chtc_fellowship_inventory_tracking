# upon first thought - these shouldn't inherit from Exception
# making them throwable and getting a stacktrace and line number
# just doesn't seem useful here

# base class for all data errors - defines a basic __str__ method
class DataError:

    def __init__(self, file: str, message=''):
        self.message = message
        self.file = file

    def __str__(self):
        return ' '.join((self.__class__.__name__, 'in file', self.file, '\n', self.message))
       
# represents a single item missing 1 or more tags
class MissingDataError(DataError):

    def __init__(self, file: str, missing_tags: list[str], message=''):
        self.missing_tags = missing_tags
        self.file = file
        DataError.__init__(self, file, message)

    def __str__(self):
        return ''.join(( DataError.__str__(self),'\n', 
                          'offending tag(s):\n\t', 
                          ',\n\t'.join(f'  "{tag}"' for tag in self.missing_tags), '\n',
                          '_____________________________________________________', '\n'))

# a 'helper' class that associates a hostname with 2 of its tags
# one that makes the asset part of a particular group
# and another that conflicts with others in the group
class ConflictItem:
    def __init__(self, hostname: str, group: str, conflicting: str):
        self.hostname = hostname
        self.group = group
        self.conflicting = conflicting

    def __str__(self):
        return f'{self.hostname}: ("{self.group}", "{self.conflicting}")'

# represents an error where 1 or more assets in a certain group (ex. same condo_chassis)
# have other conflicting values (ex. different elevation)
class ConflictingGroupError(DataError):
    
    def __init__(self, conflicting: list[ConflictItem], message=''):
        self.conflicting = conflicting
        DataError.__init__(self, self.conflicting[0].hostname, message)

    def __str__(self):
        return ''.join(( DataError.__str__(self), '\n',
                          'the following items contain conflicts:\n\t',
                          ',\n\t'.join(str(confl) for confl in self.conflicting), '\n',
                          '_____________________________________________________', '\n'))
