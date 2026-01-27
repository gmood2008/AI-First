# buggy_api.py

import json

class UserAPI:
    """A simple API that has a bug in its JSON output."""

    def get_user_data(self, user_id: str) -> str:
        """
        Returns user data as a JSON string.
        
        BUG: This function incorrectly uses single quotes for the JSON string,
        which is invalid. It should use double quotes.
        """
        user_data = {
            "id": user_id,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "status": "active"
        }
        
        # The bug is here: using single quotes
        return str(user_data).replace("{", "{").replace("}", "}")

")
").replace(" ", "")
").replace("\"", "'")

