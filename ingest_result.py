class IngestResult():
    def __init__(self, value):
        self.value = value

class IngestPermissionsException(IngestResult):
    pass

class IngestServerException(IngestResult):
    pass

class IngestUserException(IngestResult):
    pass

class IngestValidationException(IngestUserException):
    def __init__(self, value, validation_errors):
        super().__init__(value)
        self.validation_errors = validation_errors