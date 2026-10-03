from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError
import requests, os, time

feed = gtfs_realtime_pb2.FeedMessage()
feeds = {
    "trips": "https://metromap.cityofmadison.com/gtfsrt/trips",
    "vehicles": "https://metromap.cityofmadison.com/gtfsrt/vehicles",
    "alerts": "https://metromap.cityofmadison.com/gtfsrt/alerts",
}

while True:
    for name, url in feeds.items():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.content
            feed.ParseFromString(data)

            foldername = os.path.join("data_collection", "data", "raw", name)
            os.makedirs(foldername, exist_ok=True)
            filename = str(feed.header.timestamp) + ".pb"
            filepath = os.path.join(foldername, filename)

            with open(filepath, "wb") as f:
                f.write(response.content)

        except requests.exceptions.HTTPError as err:
            print(f"[{name}] The server returned an HTTP error code: {err}")
        except requests.exceptions.RequestException as e:
            print(f"[{name}] Error fetching GTFS data: {e}")
        except DecodeError as e:
            print(f"[{name}] Error decoding GTFS data: {e}")
        except Exception as e:
            print(f"[{name}] An unexpected error occurred: {e}")
    time.sleep(30)