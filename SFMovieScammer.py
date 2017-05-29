import datetime
import random
import time
from splinter import Browser
from SFApi import SFApiManager,SFMovie, SFShow, SFScreen
from datetime import timedelta
from dateutil.parser import parse
from apscheduler.schedulers.blocking import BlockingScheduler

class MovieCheckin:

    USERNAME = 'user@name.net'
    PASSWORD = 'password'
    CITY = 'Linköping'
    CITY_ALIAS = 'Filmstaden Linköping'
    SEEN_MOVIES_FILENAME = 'seen_movies.txt'

    def __init__(self):
        self.manager = SFApiManager()
        self.seen_movies = self.get_seen_movies()
        print("{} - Starting MovieCheckinManager..".format(datetime.datetime.now()))
        print("List of Ids for seen movies: {}".format(self.seen_movies))
        self.todays_show = None
        self.scheduler = BlockingScheduler(timezone="Europe/Stockholm")
        self.scheduler.add_job(self.reset, 'cron', day_of_week='mon-sun', hour=8, minute=0,second=00)
        self.browser = Browser('firefox')
        self.scheduler.start()

    def reset(self):
        print("{} - Job: time to select a new movie".format(datetime.datetime.now()))
        self.todays_show = self.select_show()
        show_length = self.todays_show.get_show_length()
        self.todays_show_end = self.todays_show.time + timedelta(minutes=show_length + 10)
        print("Selected movie {} which begins at {} and ends at {}".format(self.todays_show.movie.title,self.todays_show.time,self.todays_show_end))
        five_minutes_before_movie_start = self.todays_show.time - timedelta(minutes=5)
        print("Registering job to run @ {}".format(five_minutes_before_movie_start))
        self.scheduler.add_job(self.get_taken_seat, 'date', run_date=five_minutes_before_movie_start, id='seat_job')

    def get_taken_seat(self):
        print("{} - Job: five minutes before show starts, selecting taken seat..".format(datetime.datetime.now()))
        self.seat = self.todays_show.get_taken_seat()
        if self.seat != None:
            print("Selected taken seat: {}".format(self.seat))
            print("Registering job to run @ {}".format(self.todays_show_end))
            self.scheduler.add_job(self.register, 'date', run_date=self.todays_show_end, id='register_job')
        else:
            "No-one purchased tickets to this show, trying another movie.."
            self.reset()

    def get_seen_movies(self):
        seen_movies_file = open(self.SEEN_MOVIES_FILENAME,'r')
        seen_movies = [id.rstrip() for id in seen_movies_file.readlines()]
        seen_movies_file.close()
        return seen_movies

    def add_seen_movie(self,movie_id):
        self.seen_movies.append(movie_id)
        print("{} - Adding movie with showId {} to file".format(datetime.datetime.now(),movie_id))
        try:
            seen_movies_file = open(self.SEEN_MOVIES_FILENAME,'a')
            seen_movies_file.write("{}\n".format(movie_id))
            seen_movies_file.close()
        except:
            print("Could not add showId to file!")

    def get_todays_lkpg_shows(self):
        date_str = datetime.datetime.today().strftime('%Y-%m-%d')
        lkpg_ncgid = [theater.ncg_id for theater in self.manager.get_theaters() if theater.city_alias == "LI"][0]
        return self.manager.get_shows(lkpg_ncgid,date_str,date_str)

    def select_show(self):
        todays_unseen_shows = [show for show in self.get_todays_lkpg_shows() if show.movie.ncg_id not in self.seen_movies and show.time > datetime.datetime.now()]
        selected_show = random.choice(todays_unseen_shows)
        selected_show.seats = self.manager.get_seats(selected_show.remote_entity_id)
        print("Todays movie selected: {}".format(selected_show.movie.title))
        print("Ncg-Id: {}".format(selected_show.movie.ncg_id))
        print("Id: {}".format(selected_show.remote_entity_id))
        print("Starts: {}".format(selected_show.time))
        return selected_show

    def register(self):
        print("{} - Job: time to register todays show!".format(datetime.datetime.now()))
        cityStr = self.CITY
        cinemaStr = self.CITY_ALIAS
        dateStr = self.todays_show.time.strftime("%Y-%m-%d")
        timeStr = self.todays_show.time.strftime("%H:%m")
        roomNr = self.todays_show.remote_entity_id.split("-")[1]
        seatNr = self.seat[1]
        rowNr = self.seat[0]
        movieTitleStr = self.todays_show.movie.title

        url = "http://www3.sf.se/BIOKLUBBEN/LOGGA-IN/"
        count = 0
        while count < 10: #dunno why one might have to try several times before it works, I blame Geckodriver..
            try:
                self.browser.visit(url)
                with self.browser.get_iframe("Stack") as iframe:
                    print("Loggar in")
                    iframe.fill('ctl00$ContentPlaceHolder1$LoginNameTextBox', self.USERNAME)
                    iframe.fill('ctl00$ContentPlaceHolder1$PasswordTextBox',self.PASSWORD)
                    iframe.click_link_by_text('Logga in')
                with self.browser.get_iframe("Stack") as iframe:
                    print("Fyller i uppgifter")
                    iframe.click_link_by_text("Efterregistrering")
                    iframe.select('ctl00$ContentPlaceHolder1$CinemaNameDDL',cinemaStr)
                    iframe.fill('ctl00$ContentPlaceHolder1$TransactionDateTextBox',dateStr)
                    iframe.fill('ctl00$ContentPlaceHolder1$RowNbrTextBox', rowNr)
                    iframe.fill('ctl00$ContentPlaceHolder1$ShowTimeTextBox', timeStr)
                    iframe.select('ctl00$ContentPlaceHolder1$CityNameDDL', cityStr)
                    iframe.fill('ctl00$ContentPlaceHolder1$SalonIDTextBox', roomNr)
                    iframe.fill('ctl00$ContentPlaceHolder1$MovieNameTextBox', movieTitleStr)
                    iframe.fill('ctl00$ContentPlaceHolder1$ChairNbrTextBox', seatNr)
                    iframe.click_link_by_text("Skicka")
                    print("{} - Sent registration!".format(datetime.datetime.now()))
                    count = 10
                    break
            except:
                count = count + 1
        self.add_seen_movie(self.todays_show.movie.ncg_id)

mc = MovieCheckin()
