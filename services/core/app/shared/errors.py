class ScholarSetuError(Exception):
    pass

class NotFoundError(ScholarSetuError):
    pass

class ConflictError(ScholarSetuError):
    pass

class ValidationError(ScholarSetuError):
    pass

class AuthorizationError(ScholarSetuError):
    pass

class ExternalServiceError(ScholarSetuError):
    pass

class AdapterError(ScholarSetuError):
    pass

class ConsentRequiredError(ScholarSetuError):
    pass

class ConsentExpiredError(ScholarSetuError):
    pass

class SchemeConflictError(ScholarSetuError):
    pass

class AttestationExpiredError(ScholarSetuError):
    pass
