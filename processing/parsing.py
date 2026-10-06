import csv

with open('stop_times.txt', 'r') as file:
    reader = csv.DictReader(file)
    schedule = {}
    for row in reader:
        trip_id = row['trip_id']
        arrival_time = row['arrival_time']
        departure_time = row['departure_time']
        stop_id = row['stop_id']
        stop_sequence = row['stop_sequence']
        schedule[trip_id, int(stop_sequence)] = arrival_time
    print(schedule["127020", 34])