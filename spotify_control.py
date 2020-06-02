# -*- coding: utf-8 -*-
import json
import subprocess
import httplib, urllib
from threading import Thread

from player_base import PlayerBase
#import config

class SpotifyControl (PlayerBase):
    def __init__(self, config):
        super(SpotifyControl, self).__init__("spotify", config)

        self.client = None
        self.noConnection = False

        self.capabilities["volume_enabled"]  = self.config.volume_enabled
        self.capabilities["random_enabled"]  = True
        self.capabilities["repeat_enabled"]  = True
        self.capabilities["logopath"]        = "pics/logo/spotify.png"

        # Helper variable for old volume data
        # because it is delivered in song, not status
        self.volume = ""

        # Active client in spotify?
        self.active_client = False

        self.connect()

    def __getitem__(self, item):
        return self.data[item]

    def __call__(self, item):
        return self.capabilities[item]

    def refresh(self, active=False):
        status = {}
        song = {}

        if not self.client:
            self.connect()
        else:
            try:
                # Fetch status
                sp_status = self._api("info","status")

                # Selected player in spotify
                active_client = sp_status["active"]
                logged_in = sp_status["logged_in"]

                # Parse status
                status["state"] = "play" if sp_status["playing"] and active_client else "pause"
                status["random"] = 1 if sp_status["shuffle"] else 0
                status["repeat"] = 1 if sp_status["repeat"] else 0
                # Get volume from previous metadata
                status["volume"] = self.volume

                # Check for changes in status
                if status != self.data["status"]:
                    if status["state"] != self.data["status"]["state"]:
                        self.data["update"]["state"]   = True
                        # Started playing on this device - request active status
                        if active_client and status["state"] == "play":
                            self.data["update"]["active"] = True

                    if status["repeat"] != self.data["status"]["repeat"]:
                        self.data["update"]["repeat"] = True
                    if status["random"] != self.data["status"]["random"]:
                        self.data["update"]["random"] = True
                    if status["volume"] != self.data["status"]["volume"]:
                        self.data["update"]["volume"] = True

                    #Save new status
                    self.data["status"] = status
                    self.active_client = active_client

            except Exception as e:
                if not self.noConnection:
                    self.logger.error(e)
                self._disconnected()

            try:
                if active:
                    # Fetch song info
                    sp_metadata       = self._api("info","metadata")

                    self.volume = str(int(sp_metadata["volume"])*100/65535)
                    song["album"]     = sp_metadata["album_name"].encode('utf-8')
                    song["artist"]    = sp_metadata["artist_name"].encode('utf-8')
                    song["title"]     = sp_metadata["track_name"].encode('utf-8')
                    song["cover_uri"] = sp_metadata["cover_uri"]
                    song["time"]      = ""
                    song["track"]     = ""
                    song["date"]      = ""

                    # Fetch coverart
                    if song["cover_uri"] and not self.data["cover"] or song["cover_uri"] != self.data["song"]["cover_uri"]:
                        self.logger.debug("Spotify coverart changed, fetching...")
                        self.data["cover"] = False

                        # Find cover art on different thread
                        try:
                            if self.coverartThread:
                                if not self.coverartThread.is_alive():
                                    self.coverartThread = Thread(target=self._fetch_coverart(song["cover_uri"]))
                                    self.coverartThread.start()
                            else:
                                self.coverartThread = Thread(target=self._fetch_coverart(song["cover_uri"]))
                                self.coverartThread.start()
                        except Exception as e:
                            self.logger.error("Coverartthread: %s" % e)
                    else:
                        song["coverartfile"] = self.data["coverartfile"]
                        song["cover"] = self.data["cover"]

                    # Check for changes in song
                    if song != self.data["song"]:
                        if (
                                song["artist"] != self.data["song"]["artist"] or
                                song["album"]  != self.data["song"]["album"]  or
                                song["title"]  != self.data["song"]["title"]
                        ):
                            self.data["update"]["trackinfo"] = True
                        if song["album"] != self.data["song"]["album"]:
                            self.data["update"]["coverart"] = True

                        # Save new song info
                        self.data["song"] = song

            except Exception as e:
                self.logger.error(e)
                self._disconnected()

    def connect (self):
        if not self.noConnection:
            self.logger.info("Trying to connect to Spotify server")

        self.client = httplib.HTTPConnection(self.config.spotify_host, self.config.spotify_port)
        try:
            displayname = self._api("info","display_name")
            self.logger.info("Spotify connected")
            self.noConnection = False
            self.capabilities["connected"]   = True
        except Exception as e:
            if not self.noConnection:
                self.logger.error(e)
            self._disconnected()
            self.noConnection = True
            self.capabilities["connected"]   = False

    def _disconnected(self):
        if not self.noConnection:
            self.logger.info("Lost connection to Spotify server")
        self.capabilities["connected"] = False
        self.init_data()
        self.client = None
        self.noConnection = True

    def control(self, command, parameter=-1):
        # Translate commands
        if command == "stop":
            command = "pause"
        if command == "previous":
            command = "prev"
        if command == "random":
            command = "shuffle"
        if command == "volume" and parameter != -1:
            parameter = parameter*65535/100

        # Prevent commands not implemented in api
        if command in ["play", "pause", "prev", "next", "shuffle", "repeat", "volume"]:

            # Check shuffle and repeat state
            if command == "shuffle":
                command += '/disable' if self.data["status"]["random"] else '/enable'

            if command == "repeat":
                command += '/disable' if self.data["status"]["repeat"] else '/enable'

            #Send command
            try:
                if self.client:
                    self._api("playback", command, parameter)
            except Exception as e:
                self.logger.error(e)
                self._disconnected()

    def _fetch_coverart(self, cover_uri):
        self.data["cover"] = False
        self.data["coverartfile"] = ""
        try:
            if self.client:
                coverart_url = self.config.spotify_host + ":" + self.config.spotify_port + "/api/info/image_url/" + cover_uri
                if coverart_url:
                    self.data["coverartfile"] = self.config.logpath + "/sp_cover.png"
                    subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.data["coverartfile"]), shell=True )
                    self.logger.debug("Spotify coverart downloaded")
                    self.data["cover"] = True
                    self.data["update"]["coverart"] = True
        except Exception as e:
            self.logger.error(e)
            pass

    # Using api from spotify-connect-web
    # Valid methods:  playback, info
    # Valid info commands: metadata, status, image_url/<image_url>, display_name
    # Valid playback commands: play, pause, prev, next, shuffle[/enable|disable], repeat[/enable|disable], volume
    def _api(self, method, command, parameter=0):
        if command != "volume":
            self.client.request('GET', '/api/'+method+'/'+command, '{}')
        else:
            params = urllib.urlencode({"value": parameter})
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
            self.client.request('POST', '/api/'+method+'/'+command, params, headers)

        doc = self.client.getresponse().read()
        try:
            doc = json.loads(doc)
        except:
            doc = doc
        return doc
