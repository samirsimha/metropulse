from google.transit import gtfs_realtime_pb2 
from datetime import datetime   
from zoneinfo import ZoneInfo
import csv

prediction = {}
feed = gtfs_realtime_pb2.FeedMessage()
with open('data_collection/data/raw/trips/1791156944.pb', 'rb') as f:
    feed.ParseFromString(f.read())
for entity in feed.entity:
    if entity.trip_update.trip.HasField('trip_id'):
        trip_id = entity.trip_update.trip.trip_id
    else:
        trip_id = entity.trip_update.trip.modified_trip.affected_trip_id
    for stop in entity.trip_update.stop_time_update:
        stop_sequence = int(stop.stop_sequence)
        if stop.HasField('arrival'):
            arrival_time = stop.arrival.time
        else:
            arrival_time = stop.departure.time
        prediction[trip_id, stop_sequence] = (arrival_time, stop.stop_id, entity.trip_update.trip.route_id)

tz = ZoneInfo("America/Chicago")
local = datetime.fromtimestamp(feed.header.timestamp, tz)
midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)  
with open('stop_times.txt', 'r') as file:
    reader = csv.DictReader(file)
    schedule = {}
    for row in reader:
        trip_id = row['trip_id']

        # arrival time calculation
        arrival_time_list = row['arrival_time'].split(':')
        arrival_time = int(midnight.timestamp() + int(arrival_time_list[0]) * 3600 + int(arrival_time_list[1]) * 60 + int(arrival_time_list[2]))

        # departure time calculation
        departure_time_list = row['departure_time'].split(':')
        departure_time = int(midnight.timestamp() + int(departure_time_list[0]) * 3600 + int(departure_time_list[1]) * 60 + int(departure_time_list[2]))
        
        stop_id = row['stop_id']
        stop_sequence = row['stop_sequence']
        schedule[trip_id, int(stop_sequence)] = (arrival_time, stop_id)

    snapshot_time = feed.header.timestamp

with open('delays_1791156944.csv', 'w', newline='') as out:
    writer = csv.writer(out)
    writer.writerow(['snapshot_time', 'trip_id', 'route_id', 'stop_sequence', 'stop_id',
                     'predicted', 'scheduled', 'delay_s', 'lead_time_s'])

    for key in prediction:
        if key in schedule and prediction[key][1] == schedule[key][1]:
            predicted, stop_id, route_id = prediction[key]
            scheduled = schedule[key][0]
            writer.writerow([snapshot_time, key[0], route_id, key[1], stop_id,
                             predicted, scheduled,
                             predicted - scheduled,
                             predicted - snapshot_time])