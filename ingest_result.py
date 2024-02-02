class IngestResult():
    def __init__(self, value=None):
        self.value = value

class IngestSuccess(IngestResult):
    pass

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

class IngestCohortException(IngestUserException):
    pass