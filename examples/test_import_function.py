"""
Example Python function for testing Smart Importer.
"""

import requests


def send_slack_message(channel: str, message: str, token: str) -> dict:
    """Send a message to a Slack channel.
    
    Args:
        channel: Slack channel ID or name (e.g., "#general" or "C1234567890")
        message: Message text to send
        token: Slack API token (starts with xoxb-)
    
    Returns:
        dict: Response from Slack API containing:
            - ok: bool - Whether the request was successful
            - ts: str - Timestamp of the message
            - channel: str - Channel ID where message was posted
    
    Raises:
        requests.HTTPError: If the API request fails
    """
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": channel, "text": message}
    )
    response.raise_for_status()
    return response.json()
