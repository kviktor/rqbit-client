class RQBitError(Exception):
    pass


class RQBitHTTPError(RQBitError):
    def __init__(self, response):
        status_code = response.status_code

        try:
            error_message = response.json()
        except Exception:
            error_message = response.text

        message = f"HTTP {status_code}, response: {error_message}"
        super().__init__(message)
