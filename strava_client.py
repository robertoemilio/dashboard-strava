import streamlit as st

CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]

def get_access_token():
    url = "https://www.strava.com/oauth/token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    res = requests.post(url, data=payload)
    res.raise_for_status()

    return res.json()["access_token"]


def get_activities():
    token = get_access_token()

    url = "https://www.strava.com/api/v3/athlete/activities"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    all_data = []
    page = 1

    while True:
        params = {
            "per_page": 50,
            "page": page
        }

        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()

        data = res.json()

        if not data:
            break

        all_data.extend(data)
        page += 1

    return all_data