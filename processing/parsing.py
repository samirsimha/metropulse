from google.transit import gtfs_realtime_pb2 
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.protobuf.message import DecodeError
from collections import defaultdict

import pandas as pd
import csv, glob
tz = ZoneInfo("America/Chicago")

"""
populating schedule dictionary mapping every trip id and each of its stops (sequence id)
to its scheduled time of arrival and the id of the stop for a single service day -- RUNS ONCE
"""
with open('stop_times.txt', 'r') as file:
    reader = csv.DictReader(file)
    schedule = {}
    for row in reader:
        trip_id = row['trip_id']

        # arrival time calculation
        arrival_time_list = row['arrival_time'].split(':')
        arrival_time = int(arrival_time_list[0]) * 3600 + int(arrival_time_list[1]) * 60 + int(arrival_time_list[2])

        #departure time calculation
        #departure_time_list = row['departure_time'].split(':')
        #departure_time = int(midnight.timestamp() + int(departure_time_list[0]) * 3600 + int(departure_time_list[1]) * 60 + int(departure_time_list[2]))
        
        stop_id = row['stop_id']
        stop_sequence = row['stop_sequence']
        schedule[trip_id, int(stop_sequence)] = (arrival_time, stop_id)

files = glob.glob('data_collection/data/raw/trips/*.pb')
by_date = defaultdict(list)
skipped = 0

columns = ['snapshot_time', 'trip_id', 'route_id', 'stop_sequence', 'stop_id',
                    'predicted', 'scheduled', 'delay_s', 'lead_time_s', 'service_date'] 
for file in files:
    feed = gtfs_realtime_pb2.FeedMessage()
    prediction = {}
    try:
        with open(file, 'rb') as f:
            feed.ParseFromString(f.read())
    except (OSError, DecodeError) as err:
        print(f"skipping {file}: {err}")
        skipped += 1
        continue
    if feed.header.timestamp == 0:
        print(f"skipping {file}: empty feed (timestamp 0)")
        skipped += 1
        continue
    """
    populating prediction dictionary mapping a trip id and each of its stops (sequence id)
    to its predicted time of arrival (if the trip hasn't arrived at that stop yet)
    or its actual time of arrival (if the trip has arrived at that stop already),
    as well as the id of the stop in the madison metro system and the id of the bus route
    """

    for entity in feed.entity:
        if entity.trip_update.trip.HasField('trip_id'):
            trip_id = entity.trip_update.trip.trip_id
        else:
            trip_id = entity.trip_update.trip.modified_trip.affected_trip_id
        for stop in entity.trip_update.stop_time_update:
            stop_sequence = int(stop.stop_sequence)
            if stop.schedule_relationship == gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SCHEDULED:
                if stop.HasField('arrival'):
                    arrival_time = stop.arrival.time
                else:
                    arrival_time = stop.departure.time
                prediction[trip_id, stop_sequence] = (arrival_time, stop.stop_id, entity.trip_update.trip.route_id)

    """
    matches the key (trip id and stop sequence) in prediction dictionary
    to its counterpart in the trip schedule dictionary and then finds the delay
    in predicted/actual time of arrival to the scheduled time of arrival 
    and writes each pair to a csv per snapshot
    """

    # calculating the three proposed midnight timestamps to use
    snapshot_time = feed.header.timestamp
    local = datetime.fromtimestamp(feed.header.timestamp, tz)
    today_midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    yest_midnight = today_midnight - timedelta(days=1)
    tmr_midnight = today_midnight + timedelta(days=1)

    today_midnight = today_midnight.timestamp()
    yest_midnight = yest_midnight.timestamp()
    tmr_midnight = tmr_midnight.timestamp()


    for key in prediction:
        if key in schedule and prediction[key][1] == schedule[key][1]:
            predicted, stop_id, route_id = prediction[key]

            # calculating which midnight to use for delay calculation
            best_midnight = min([today_midnight, yest_midnight, tmr_midnight], key=lambda m: abs(predicted - (m + schedule[key][0])))
            
            service_date = datetime.fromtimestamp(best_midnight, tz).date()
            
            scheduled = int(best_midnight + schedule[key][0])
            by_date[service_date].append([snapshot_time, key[0], route_id, key[1], stop_id,
                            predicted, scheduled,
                            predicted - scheduled,
                            predicted - snapshot_time, service_date])
for date in by_date:
    pd.DataFrame(by_date[date], columns=columns).to_parquet(f"data_collection/data/processed/delays_{date}.parquet", index=False)
    print(f"wrote delays_{date}.parquet: {len(by_date[date])} rows")
print(f"done: processed {len(files) - skipped} of {len(files)} files, skipped {skipped}")