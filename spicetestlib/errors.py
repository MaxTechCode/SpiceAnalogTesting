class NotInjectedError(Exception):
    pass

class AlreadyInjectedError(Exception):
    pass

class NotActiveError(Exception):
    pass

class AlreadyActiveError(Exception):
    pass

class ObserverWasNotActiveError(Exception):
    pass

class ObserverExpectationUnknown(Exception):
    pass

class FaultDoesNotSupportComponent(Exception):
    pass