#!/usr/bin/env python3

from flask import Flasks, request, jsonify
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
import logging
from datetime import datetime, timedelta, timezone
import math
import requests
import pytz
import time
from astropy import coordinates
from astropy import units
from astropy.time import Time
from geopy.geocoders import Nominatim

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ISS_DATA_URL = 'https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml'

def compute_location_astropy(sv):
    x = float(sv['x'])
    y = float(sv['y'])
    z = float(sv['z'])

    # assumes epoch is in format '2024-067T08:28:00.000Z'
    this_epoch=time.strftime('%Y-%m-%d %H:%m:%S', time.strptime(sv['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))

    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

    return loc.lat.value, loc.lon.value, loc.height.value
 

def get_xml_data():
    response = requests.get(ISS_DATA_URL)
    return ET.fromstring(response.content)

def fetch_iss_data(url: str) -> str:
    """
    Fetches the ISS trajectory data from the specified URL using the requests library.

    Args:
        url (str): The URL from which to fetch the ISS data.

    Returns:
        str: The content of the ISS data as a string if successful, None otherwise.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching ISS data: {e}")
        return None

@app.route('/epochs?limit=int&offset=int', methods=['GET'])
def parse_oem_data(xml_content: str) -> List[Dict]:
    """
    Parses the OEM data from an XML content string and returns it as a list of dictionaries.

    Args:
        xml_content (str): The XML content as a string.

    Returns:
        List[Dict]: A list of dictionaries with the parsed data.
    """
    try:
        root = ET.fromstring(xml_content)
        data = []
        for state_vector in root.iter('stateVector'):
            data_point = {
                'epoch': state_vector.find('EPOCH').text,
                'x': float(state_vector.find('X').text),
                'y': float(state_vector.find('Y').text),
                'z': float(state_vector.find('Z').text),
                'x_dot': float(state_vector.find('X_DOT').text),
                'y_dot': float(state_vector.find('Y_DOT').text),
                'z_dot': float(state_vector.find('Z_DOT').text)
            }
            data.append(data_point)
        return data
        offset = int(request.args.get("offset", 0))
        if offset<0:
            raise ValueError
        limit = int(request.args.get("limit",0))
        if limit<0:
            raise ValueError
    except ET.ParseError as e:
        logging.error(f"Error parsing the XML content: {e}")
        raise
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

@app.route('/epochs/<epoch>', methods=['GET'])
def parse_approximate_time(time_str: str) -> datetime:
    """
    Parses the time string to a datetime object, accommodating for different formats
    that might include or exclude the day or fractional seconds.
    """
    formats = [
        '%Y-%jT%H:%M:%S.%fZ',  # Format with ordinal day and fractional seconds
        '%Y-%jT%H:%M:%SZ',     # Format with ordinal day, without fractional seconds
        '%Y-%m-%dT%H:%M:%S.%fZ',  # Format with month-day and fractional seconds
        '%Y-%m-%dT%H:%M:%SZ',     # Format with month-day, without fractional seconds
        # ... you can add more formats if needed
    ]

    for fmt in formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            if fmt.endswith('Z'):
                return parsed_time.replace(tzinfo=timezone.utc)
            return parsed_time
        except ValueError:
            continue

    error_message = f"Time data '{time_str}' does not match any of the known formats"
    logging.error(error_message)
    raise ValueError(error_message)

@app.route('epoch/<epoch>/speed', methods=['GET'])
def calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    """
    Calculates the speed from Cartesian velocity vectors.

    Args:
        x_dot (float): Velocity in the x direction.
        y_dot (float): Velocity in the y direction.
        z_dot (float): Velocity in the z direction.

    Returns:
        float: The calculated speed.
    """
    return math.sqrt(x_dot**2 + y_dot**2 + z_dot**2)

@app.route('/now', methods=['GET'])
def get_instantaneous_speed(data: List[Dict], closest_time: datetime) -> Tuple[Dict, float]:
    """
    Gets the instantaneous speed for the state vector closest to the given time.

    Args:
        data (List[Dict]): The list of state vectors.
        closest_time (datetime): The time to find the closest state vector to.

    Returns:
        Tuple[Dict, float]: The closest state vector and its speed.
    """
    # Ensure that closest_time is offset-aware
    closest_time = closest_time.replace(tzinfo=timezone.utc)

    closest_vector = None
    min_time_diff = timedelta.max

    for point in data:
        point_time = parse_approximate_time(point['epoch'])

        # If point_time is not timezone-aware, assign UTC timezone to it
        if point_time.tzinfo is None:
            point_time = point_time.replace(tzinfo=timezone.utc)

        # Calculate the time difference
        time_diff = abs(point_time - closest_time)

        if time_diff < min_time_diff:
            min_time_diff = time_diff
            closest_vector = point

    if closest_vector is None:
        raise ValueError("Could not find the closest vector.")

    speed = calculate_speed(closest_vector['x_dot'], closest_vector['y_dot'], closest_vector['z_dot'])
    return closest_vector, speed

def get_average_speed(data: List[Dict]) -> float:
    """
    Calculates the average speed over the provided dataset.

    Args:
        data (List[Dict]): The list of state vectors.

    Returns:
        float: The average speed.
    """
    total_speed = sum(calculate_speed(point['x_dot'], point['y_dot'], point['z_dot']) for point in data)
    return total_speed / len(data)

@app.route('/epochs', methods=['GET'])
def print_data_range(data: List[Dict]):
    """
    Prints the range of data using timestamps from the first and last epochs.

    Args:
        data (List[Dict]): The list of state vectors.
    """
    if data:
        start_epoch = data[0]['epoch']
        end_epoch = data[-1]['epoch']
        print(f"The range of data is from {start_epoch} to {end_epoch}")

@app.route('/comment', methods=['GET'])
def comment():
    root = get_xml_data()
    comments = root.find('comment').text.splitlines()  #assumes comments are newline separated
    return jsonify(comments)

@app.route('/header', methods=['GET'])
def header():
    root = get_xml_data()
    header = {child.tag: child.text for child in root.find('header')}
    return jsonify(header)

@app.route('/metadata', methods=['GET'])
def metadata():
    root = get_xml_data()
    metadata = {child.tag: child.text for child in root.find('metadata')}
    return jsonify(metadata)

@app.route('/epochs/<epoch>/location', methods=['GET'])
def epoch_location(epoch):
    root = get_xml_data()
    for state_vector in root.iter('stateVector'):
        if state_vector.find('EPOCH').text == epoch:
            latitude, longitude, altitude = compute_location_astropy(state_vector)
            coordinates = f'{latitude}, {longitude}'
            geolocator = Nominatim(user_agent="iss_tracker_app")
            location = geolocator.reverse(coordinates, zoom=15, language="en")
        if location is None:
            location = "Over the ocean"
        location =  location.raw["display_name"]
    return jsonify({
        'latitude': state_vector.find('latitude').text,
        'longitude': state_vector.find('longitude').text,
    })
    return 'Epoch not found', 404

@app.route('/now', methods=['GET'])
def now():
    root = get_xml_data()
    closest_state_vector = None
    min_time_diff = None
    now = datetime.now(pytz.utc)
    for state_vector in root.iter('stateVector'):
        epoch = datetime.strptime(state_vector.find('EPOCH').text, '%Y-%jT%H:%M:%SZ')
        epoch = epoch.replace(tzinfo=pytz.utc)
        time_diff = abs((now - epoch).total_seconds())
        if min_time_diff is None or time_diff < min_time_diff:
            min_time_diff = time_diff
            closest_state_vector = state_vector
    if closest_state_vector: 
        latitude, longitude, altitude = compute_location_astropy(closest_state_vector)
        location =  location.raw["display_name"]
        coordinates = f'{latitude}, {longitude}'
        geolocator = Nominatim(user_agent="iss_tracker_app")
        location = geolocator.reverse(coordinates, zoom=15, language="en")     
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude,
        })
    return 'Current location not found', 404

def main():
    """
    Main execution function to process the ISS OEM data from XML content.

    Args:
        xml_content (str): The XML content as a string.
    """

    iss_data_url = 'https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml'

    try:
        xml_content = fetch_iss_data(iss_data_url)
        if xml_content is None:
            raise ValueError("Failed to fetch ISS data")

        data = parse_oem_data(xml_content)

        average_speed = get_average_speed(data)
        logging.info(f"Average speed over the whole dataset: {average_speed:.2f} m/s")

        closest_time = datetime.utcnow()
        closest_vector, instantaneous_speed = get_instantaneous_speed(data, closest_time)
        logging.info(f"State vector closest to now ({closest_time}): {closest_vector}")
        logging.info(f"Instantaneous speed closest to now: {instantaneous_speed:.2f} m/s")

        print(f"State vector closest to now: {closest_vector}")
        print(f"Instantaneous speed closest to now: {instantaneous_speed:.2f} m/s")

        print_data_range(data)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
    app.run(debug=True, host='0.0.0.0')  
