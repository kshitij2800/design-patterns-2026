class PolicyBlockedError(Exception):
    """Raised by a decorator that rejects an apply() call instead of calling the inner port."""

    def __init__(self, policy_name: str, message: str) -> None:
        super().__init__(message)
        self.policy_name = policy_name
        self.message = message