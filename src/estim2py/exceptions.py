from typing import override

class Estim2pyError(Exception):
    def __init__(self, message: str, data: str | None = None):
        super().__init__(message)
        self.data: str | None = data

    @override
    def __str__(self):
        # This makes the error message very helpful in your logs
        return f"{self.args[0]} ({self.data if self.data else 'no data'})"
