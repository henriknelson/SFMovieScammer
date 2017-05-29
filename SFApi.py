import requests
import json
from datetime import timedelta
from dateutil.parser import parse
import random
import pprint

class SFSeat:
    def __init__(self,seat):
        self.id = seat["id"]
        self.isAvailable = seat["isAvailable"]

class SFMovie:
    def __init__(self,ncg_id,title):
        self.ncg_id = ncg_id
        self.title = title

class SFTheater:
    def __init__(self, ncg_id, title, city, city_alias):
        self.ncg_id = ncg_id
        self.title = title
        self.city = city
        self.city_alias = city_alias

class SFScreen:
    def __init__(self,ncg_id,title,seat_count):
        self.ncg_id = ncg_id
        self.title = title
        self.seat_count = seat_count

class SFShow:
    def __init__(self,show_dict,seats=None):
        self.manager = SFApiManager()
        self.time = parse(show_dict["time"]).replace(tzinfo=None) + timedelta(hours=2)
        self.remote_entity_id = show_dict["remoteEntityId"]
        self.movie = SFMovie(show_dict["movie"]["ncgId"],show_dict["movie"]["title"])
        self.cinema = SFTheater(show_dict["cinema"]["ncgId"],show_dict["cinema"]["title"],show_dict["cinema"]["address"]["city"]["name"],show_dict["cinema"]["address"]["city"]["alias"])
        if "screen" in show_dict:
            self.screen = SFScreen(show_dict["screen"]["ncgId"],show_dict["screen"]["title"],show_dict["screen"]["seatCount"])
        else:
            self.screen = None
        self.seats = seats

    def get_taken_seat(self):
        seats = self.manager.get_seats(self.remote_entity_id)
        if len(seats["not_available"]) > 0:
            return random.choice(seats["not_available"])[1]
        else:
            return None

    def get_show_length(self):
        length = self.manager.get_show_length(self.remote_entity_id)
        return length

class SFApiManager:

    URL = 'www.sf.se/'

    def __init__(self):
        self.client = requests.Session()

    def request(self,endpoint,parameters = {}):
        url = 'https://%s%s?' % (self.URL,endpoint)
        print("Sending request to {}".format(url))
        r = self.client.request('GET', url, params=parameters)
        response = json.loads(r.content.decode())
        return response

    def get_theaters(self):
        endpoint = "api/v1/cinemas/category/"
        params = { "Page" : 1 }
        response = self.request(endpoint,params)
        theaters = []
        for theater in response:
            theaters.append(SFTheater(ncg_id=theater['ncgId'],title=theater['title'],city=theater['address']['city']['name'],city_alias=theater['address']['city']['alias']))
        return theaters

    def get_shows(self,cinema_ncg_id=None,start_time=None,end_time=None):
        endpoint = "api/v2/show/sv/1/100"
        params = {"filter.cinemaNcgId" : cinema_ncg_id,"filter.timeUtc.greaterThanOrEqualTo" : start_time,"filter.timeUtc.lessThanOrEqualTo" : end_time}
        response = self.request(endpoint,params)
        shows = []
        for show in response["items"]:
                shows.append(SFShow(show))
        return shows

    def get_seat_information(self,remote_entity_id):
        endpoint = "api/v1/shows/showmetadata/"
        params = { "remoteSystemAlias": "Sys99-SE","showId": remote_entity_id }
        response = self.request(endpoint, params)
        seats = response["screen"]["seats"]
        res_dict = {}
        for seat in seats:
            res_dict.setdefault(seat["id"],(seat["row"],seat["seatNumber"]))
        return res_dict

    def get_seats(self,showId):
        endpoint = "api/v1/shows/seats/status"
        params = { "remoteSystemAlias" : "Sys99-SE","showId" : showId }
        response = self.request(endpoint,params)
        seat_info_dict = self.get_seat_information(showId)
        res_dict = {}
        available = []
        not_available = []
        for seat in response["seatStatuses"]:
            seat_id = seat['id']
            if seat["isAvailable"] == True:
                available.append((seat_id,seat_info_dict[seat_id]))
            else:
                not_available.append((seat_id,seat_info_dict[seat_id]))
        res_dict.setdefault("available",available)
        res_dict.setdefault("not_available",not_available)
        return res_dict

    def get_show_length(self,remote_entity_id):
        endpoint = "api/v1/shows/showmetadata/"
        params = { "remoteSystemAlias": "Sys99-SE","showId": remote_entity_id }
        response = self.request(endpoint, params)
        length = response["show"]["movieLength"]
        return length