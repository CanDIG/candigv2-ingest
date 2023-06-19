class IngestResult():
    def __init__(self, value):
        self.value = value

class IngestPermissionsException(IngestResult):
    pass

class IngestServerException(IngestResult):
    pass

class IngestUserException(IngestResult):
    pass