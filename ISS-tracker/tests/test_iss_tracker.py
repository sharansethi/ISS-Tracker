import pytest
from iss_tracker import parse_oem_data, calculate_speed, get_average_speed, get_instantaneous_speed
from datetime import datetime
# Sample XML data for testing
SAMPLE_XML = """
<root>
    <stateVector>
        <EPOCH>2024-02-23T00:00:00Z</EPOCH>
        <X>678.0</X>
        <Y>678.0</Y>
        <Z>678.0</Z>
        <X_DOT>1.0</X_DOT>
        <Y_DOT>0.0</Y_DOT>
        <Z_DOT>0.0</Z_DOT>
    </stateVector>
    <stateVector>
        <EPOCH>2024-02-24T00:00:00Z</EPOCH>
        <X>700.0</X>
        <Y>700.0</Y>
        <Z>700.0</Z>
        <X_DOT>0.0</X_DOT>
        <Y_DOT>1.0</Y_DOT>
        <Z_DOT>0.0</Z_DOT>
    </stateVector>
</root>
"""

# The actual tests

def test_parse_oem_data():
    """
    Test the parse_oem_data function to ensure it correctly parses XML content.
    The test verifies that the function does not return None, the number of parsed items
    matches expected state vectors, and the first epoch's value is correct.
    """
    data = parse_oem_data(SAMPLE_XML)
    assert data is not None, "Parsing returned None"
    assert len(data) == 2, "Parsing did not return expected number of state vectors"
    assert data[0]['epoch'] == "2024-02-23T00:00:00Z", "First epoch is not correct"


def test_calculate_speed():
    """
    Test the calculate_speed function to ensure it computes the speed correctly.
    The test checks the function with a unit vector along the x-axis, expecting a speed of 1.
    """
    speed = calculate_speed(1, 0, 0)
    assert speed == 1, "Speed calculation is incorrect for unit vector along x-axis"

def test_get_average_speed():
    """
    Test the get_average_speed function to verify that it calculates the correct average speed.
    It uses a small data set with known values and checks if the calculated average speed is as expected.
    """
    data = parse_oem_data(SAMPLE_XML)
    avg_speed = get_average_speed(data)
    assert avg_speed == pytest.approx(1), "Average speed calculation is incorrect"

def test_get_instantaneous_speed():
    """
    Test the get_instantaneous_speed function to ensure it finds the correct state vector closest to a given time
    and computes the speed correctly. The test uses a specific time and checks if the returned state vector and speed
    match the expected values.
    """
    data = parse_oem_data(SAMPLE_XML)
    closest_time = datetime.strptime("2024-02-23T00:00:01Z", '%Y-%m-%dT%H:%M:%SZ')
    closest_vector, speed = get_instantaneous_speed(data, closest_time)
    assert closest_vector['epoch'] == "2024-02-23T00:00:00Z", "Did not find correct closest state vector"
    assert speed == 1, "Instantaneous speed calculation is incorrect"
