from telnetlib import Telnet
from time import sleep

class CodeError(Exception):
    pass

class ExecutionError(Exception):
    pass

class CartesianPose:
    def __init__(self, x, y, z, roll, pitch, yaw):
        self.x = x
        self.y = y
        self.z = z
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def at(self, other, epsilon=.1):
        if (
            abs(self.x - other.x) < epsilon and
            abs(self.y - other.x) < epsilon and
            abs(self.z - other.x) < epsilon and
            abs(self.roll - other.roll) < epsilon and
            abs(self.pitch - other.pitch) < epsilon and
            abs(self.yaw - other.yaw) < epsilon
            ) :
            return True
        return False

PLATE_WIDTH = 81.5

class RobotArm:
    # Assuming that everything is called in sequence 
    # every function call completes before another is started

    def __init__(self, ip="192.168.0.1"):
        tn = Telnet(ip)
        self.tn = tn
        
        self.unusedStation = 0
        self.goal_id = -1

        self.send("Straight 0 -1 \n") # Set a default straight profile to use

        # Maybe want more default? 
        # Ans maybe load in some other presets to be sent on startup?

    def quit(self):
        self.send("exit")

    def send(self, command):
        self.tn.write(command.encode('ascii'))
        response = self.tn.read_until(b"\r").decode("ascii")
        code, data, _ = response.split() # response should be a string of the type "code data \r". May need to double check this though

        if code < 0:
            raise CodeError("Error code:" + code + "\ndata")

        return code, data

    '''
    Set the location of some station that we haven't yet used to the robot current position

    Return the station_id of this position
    '''
    def TeachPosition(self):
        station_id = self.unusedStation
        self.unusedStation += 1 # mark this station as under use. 

        command = "TeachPlate " + self.unusedStation + " \n"        
        self.send(command)

        return station_id

    '''
    Command the robot to move to a given station_id
    Raise an error if this station_id has not been set yet
    '''
    def MoveToStation(self, station_id, move_profile=0):
        if station_id >= self.unusedStation:
            raise IndexError
        
        self.goal_id = station_id
        command = "Move " + station_id + " " + move_profile + " \n"
        self.send(command)

    '''
    Return the current robot position and current goal position
    '''
    def GetPositionAndGoal(self):
        command = "wherec \n"
        _, data = self.send(command)

        x, y, z, yaw, pitch, roll, _ = [int(datum) for datum in data.split()]
        current_position = CartesianPose(x, y, z, roll, pitch, yaw)

        if self.goal_id == -1:
            # No goal position has yet been set?
            # What do we return here? 
            pass

        command = "loc " + self.goal_id + " \n"
        _, data = self.send(command)

        x, y, z, yaw, pitch, roll, _ = [int(datum) for datum in data.split()]
        goal_position = CartesianPose(x, y, z, roll, pitch, yaw)

        return current_position, goal_position

    '''
    Given two positions

    move to the first position
    pick up

    '''
    def PickAndPlace(self, pick_station_id, place_station_id):
        command = "PickPlate " + pick_station_id # Moves and picks up plate
        self.goal_id = pick_station_id
        self.send(command)

        # Wait until we are at the goal station
        self.waitUntilAtGoal()

        # Maybe include check that the we actually picked something up?

        command = "PlacePlate " + place_station_id
        self.goal_id = pick_station_id
        self.send(command) # Moves to drop off point for plate

        self.waitUntilAtGoal()

        command = "ReleasePlate " + (PLATE_WIDTH + 10) + " 50 \n"
        self.goal_id = pick_station_id
        self.send(command) # Drop off plate


    '''
    Doesn't return until we are at our goal pose

    Maybe unneccesary? Depends on how exactly the telnet client works. Need to figure that out better.
    '''
    def waitUntilAtGoal(self):
        while True:
            current_location, goal_location = self.GetPositionAndGoal()
            if current_location.at(goal_location): # Check that we are close enough to the goal location
                return
            else:
                sleep(0.1)