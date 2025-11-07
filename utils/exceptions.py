class CharacterNotFound(Exception):
    """Raised when a character lookup fails."""

    pass

class CharacterAlreadyExists(Exception):
    """Raised when trying to create a character when one exists"""

    pass


class ItemNotFound(Exception):
    """Raised when an item lookup fails."""

    pass


class InsufficientFunds(Exception):
    """Raised when a user cannot afford an item."""

    pass
