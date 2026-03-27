import json

def load_activities():
    with open("data/activities.json") as f:
        return json.load(f)