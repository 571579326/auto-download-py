import requests


def get_json(url: str, timeout: float):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def put_json(url: str, timeout: float):
    response = requests.put(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
