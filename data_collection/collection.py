from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError
import requests, os, time

url = "https://metromap.cityofmadison.com/gtfsrt/trips"
feed = gtfs_realtime_pb2.FeedMessage()
while True:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.content
        feed.ParseFromString(data)

        foldername = os.path.join("data_collection", "data", "raw", "trips")
        filename = str(feed.header.timestamp) + ".pb"
        filepath = os.path.join(foldername, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

    except requests.exceptions.HTTPError as err:
        print(f"The server returned an HTTP error code: {err}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GTFS data: {e}")
    except DecodeError as e:
        print(f"Error decoding GTFS data: {e}")
    time.sleep(30)
        