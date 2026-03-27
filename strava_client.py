import requests
from auth_strava import get_valid_token

BASE_URL = "https://www.strava.com/api/v3"


def get_activities(per_page=50):
    token = get_valid_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(
        f"{BASE_URL}/athlete/activities",
        headers=headers,
        params={"per_page": per_page}
    )

    response.raise_for_status()

    return response.json()