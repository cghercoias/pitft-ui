# -*- coding: utf-8 -*-
import subprocess
from threading import Thread
import time
import os
import glob

from mpd import MPDClient
import pylast

from player_base import PlayerBase

class MPDControl (PlayerBase):
    def __init__(self, config):
        super(MPDControl, self).__init__("mpd", config)

        self.capabilities["volume_enabled"]    = True
        self.capabilities["seek_enabled"]      = True
        self.capabilities["random_enabled"]    = True
        self.capabilities["repeat_enabled"]    = True
        self.capabilities["elapsed_enabled"]   = True
        self.capabilities["logopath"]          = "pics/logo/mpd.png"

        # Button icons to be used in list menus
        self.capabilities["listbuttons"]       = {"remove" : {"path" : "pics/icons/remove.png", "icon" : None},
                                                  "add"    : {"path" : "pics/icons/add.png",    "icon" : None}}

        self.previouslibraryview = {"genre": "", "artist": ""}

        self.data["menu"].append ({"name": "PLAYLIST",  "type": "listview", "listcontent": self.get_playlist})
        self.data["menu"].append ({"name": "PLAYLISTS", "type": "listview", "listcontent": self.get_playlists})
        self.data["menu"].append ({"name": "LIBRARY",   "type": "listview", "listcontent": self.list_library})

        self.client = None
        self.noConnection = False
        self.lfm_connected = False

        self.connect()
        
        if self.client:
            self.logger.info("MPD server version: %s" % self.client.mpd_version)

    def refresh(self, active=False):
        status = {}
        song = {}

        if not self.client:
            self.connect()

        else:
            try:
                status = self.client.status()
                
                # Check for changes in status
                if status != self.data["status"]:
                    if status["state"] != self.data["status"]["state"]:
                        self.data["update"]["state"] = True
                        # Started playing - request active status
                        if status["state"] == "play":
                            self.data["update"]["active"] = True
                    if status["repeat"] != self.data["status"]["repeat"]:
                        self.data["update"]["repeat"]  = True
                    if status["random"] != self.data["status"]["random"]:
                        self.data["update"]["random"]  = True
                    if status["volume"] != self.data["status"]["volume"]:
                        self.data["update"]["volume"]  = True
                    if status["state"] != "stop":
                        if status["elapsed"] != self.data["status"]["elapsed"]:
                            self.data["update"]["elapsed"] = True
                    else:
                        status["elapsed"] = ""

                    # Save new status
                    self.data["status"] = status


            except Exception as e:
                self.logger.error(e)
                self._disconnected()

            try:
                # Fetch song info
                if active:
                    song = self.client.currentsong()

                    # Sanity check
                    if "pos" not in song:
                        song["pos"] = ""

                    if "artist" not in song:
                        song["artist"] = ""

                    if "album" not in song:
                        song["album"] = ""

                    if "date" not in song:
                        song["date"] = ""

                    if "track" not in song:
                        song["track"] = ""

                    if "title" not in song:
                        song["title"] = ""

                    if "time" not in song:
                        song["time"] = ""

                    # Fetch coverart, but only if we have an album
                    if song["album"] and (self.data["song"]["album"] != song["album"]):
                        self.logger.debug("MPD coverart changed, fetching...")
                        self.data["cover"] = False

                        # Find cover art on different thread
                        try:
                            if self.coverartThread:
                                if not self.coverartThread.is_alive():
                                    self.coverartThread = Thread(target=self.fetch_coverart(song))
                                    self.coverartThread.start()
                            else:
                                self.coverartThread = Thread(target=self.fetch_coverart(song))
                                self.coverartThread.start()
                        except Exception as e:
                            self.logger.error("Coverartthread: %s" % e)

                    # Check for changes in song
                    if song != self.data["song"]:
                        if (
                                song["pos"]    != self.data["song"]["pos"]    or
                                song["artist"] != self.data["song"]["artist"] or
                                song["album"]  != self.data["song"]["album"]  or
                                song["date"]   != self.data["song"]["date"]   or
                                song["track"]  != self.data["song"]["track"]  or
                                song["title"]  != self.data["song"]["title"]  or
                                song["time"]   != self.data["song"]["time"]
                        ):
                            self.data["update"]["trackinfo"] = True
                        if song["album"] != self.data["song"]["album"]:
                            self.data["update"]["coverart"] = True
                        if song["time"] != self.data["song"]["time"]:
                            self.data["update"]["elapsed"] = True

                        # Save new song info
                        self.data["song"] = song

            except Exception as e:
                self.logger.error(e)
                self._disconnected()

    def connect(self):
        if not self.noConnection:
            self.logger.info("Trying to connect to MPD server")

        client = MPDClient()
        client.timeout = 30
        client.idletimeout = None
        if not self.client:
             try:
                client.connect(self.config.mpd_host, self.config.mpd_port)
                self.client = client
                self.logger.info("Connection to MPD server established.")
                self.noConnection = False
                self.capabilities["connected"]   = True
             except Exception as e:
                if not self.noConnection:
                    self.logger.error(e)
                self._disconnected()
                self.noConnection = True
                self.capabilities["connected"]   = False

        # (re)connect to last.fm
        if not self.lfm_connected and self.config.API_KEY and self.config.API_SECRET:
            self.connect_lfm()

    def _disconnected(self):
        # Only print once
        if not self.noConnection:
            self.logger.info("Lost connection to MPD server")
        self.capabilities["connected"]   = False
        self.init_data()
        self.client = None

    def disconnect(self):
        # Close MPD connection
        if self.client:
            self.client.close()
            self.client.disconnect()
            self.logger.debug("Disconnected from MPD")

    def control(self, command, parameter=-1):
        try:
            if self.client:
                if command == "next":
                    self.client.next()
                elif command == "previous":
                    self.client.previous()
                elif command == "pause":
                    self.client.pause()
                elif command == "play":
                    self.client.play()
                elif command == "stop":
                    self.client.stop()
                elif command == "rwd":
                    self.client.seekcur("-10")
                elif command == "ff":
                    self.client.seekcur("+10")
                elif command == "seek" and parameter != -1:
                    seektime = parameter*float(self.data["song"]["time"])
                    self.client.seekcur(seektime)
                elif command == "repeat":
                    repeat = (int(self.data["status"]["repeat"]) + 1) % 2
                    self.client.repeat(repeat)
                elif command == "random":
                    random = (int(self.data["status"]["random"]) + 1) % 2
                    self.client.random(random)
                elif command == "volume" and parameter != -1:
                    self.client.setvol(parameter)
        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def load_playlist(self, playlist, clear=False):
        try:
            if self.client:
                if clear:
                    self.client.clear()
                self.client.load(playlist)
                if clear:
                    self.play_item(0)
        except Exception as e:
            self.logger.error(e)
            self._disconnected()
            
    def remove_playlist_item(self, item):
        self.logger.debug("Removing playlist item %s" % item)
        if self.client:
            self.client.delete(item)

    def get_playlists(self):
        self.data["list"]["type"] = "playlists"
        self.data["list"]["content"] = []
        self.data["list"]["viewcontent"] = self.data["list"]["content"]
        self.data["list"]["highlight"] = -1
        self.data["list"]["position"]  = 0
        self.data["list"]["click"] = self.playlists_click
        self.data["list"]["buttons"] = [{"name"  : "append",
                                         "icon"  : self.capabilities["listbuttons"]["add"]["icon"],
                                         "action" : self.load_playlist}]
        try:
            if self.client:
                playlists = self.client.listplaylists()
                for item in playlists:
                    listitem = ""
                    if "playlist" in item:
                        listitem = item["playlist"]
                    self.data["list"]["content"].append(listitem)
        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def get_playlist(self):
        self.data["list"]["type"] = "playlist"
        self.data["list"]["content"] = []
        self.data["list"]["viewcontent"] = self.data["list"]["content"]
        self.data["list"]["click"] = self.playlist_click
        self.data["list"]["buttons"] = [{"name"  : "remove",
                                         "icon"  : self.capabilities["listbuttons"]["remove"]["icon"],
                                         "action" : self.remove_playlist_item}]
        try:
            # Todo: not updating when list is shown
            # Todo: Wrong item highlighted when removing playlist items
            self.data["list"]["highlight"] = int(self.data["song"]["pos"])
            self.data["list"]["position"]  = int(self.data["song"]["pos"])
        except Exception as e:
            self.data["list"]["highlight"] = -1
            self.data["list"]["position"]  = 0

        try:
            if self.client:
                playlist = self.client.playlistinfo()

                if playlist:
                    # Parse content
                    for item in playlist:
                        listitem = ""
                        if "title" in item:
                            listitem = str(item["title"])
                            if "artist" in item:
                                listitem = str(item["artist"]) + " - " + listitem
                            if "id" in item:
                                pos = str(int(item["pos"])+1).rjust(4, ' ')
                                listitem = pos + ". " + listitem
                        # No title, get filename
                        elif "file" in item:
                            listitem = item["file"].split("/")[-1]
                        self.data["list"]["content"].append(listitem)

        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def list_library(self, type="genre", filtertype="", filter=""):

        self.data["list"]["type"] = type
        self.data["list"]["content"] = []
        self.data["list"]["viewcontent"] = []
        self.data["list"]["highlight"] = -1
        self.data["list"]["position"]  = 0
        self.data["list"]["click"] = self.library_click
        self.data["list"]["buttons"] = []
        self.data["list"]["buttons"] = [{"name"  : "append",
                                         "icon"  : self.capabilities["listbuttons"]["add"]["icon"],
                                         "action" : self.findadd}]

        try:
            if self.client:
                if filtertype and filter:
                    self.data["list"]["content"] = self.client.list(type, filtertype, filter)
                else:
                    self.data["list"]["content"] = self.client.list(type)

                # Sorting alphabetically is fine
                if type == "genre" or type == "artist":
                    self.data["list"]["viewcontent"] = self.data["list"]["content"]

                # TODO: Add date and sort by that. viewcontent "album (date)"
                elif type == "album" and filtertype == "artist":
                    self.data["list"]["viewcontent"] = self.data["list"]["content"]

                # TODO: Add tracknumber and sort by that. viewcontent "track. title"
                elif type == "title" and filtertype == "album":
                    self.data["list"]["viewcontent"] = self.data["list"]["content"]

        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def play_item(self, number):
        try:
            if self.client:
                self.client.play(number)
        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def findadd(self, type, item, clear="False"):
        try:
            if self.client:
                if clear:
                    self.client.clear()
                self.client.findadd(type, item)
                if clear:
                    self.play_item(0)
        except Exception as e:
            self.logger.error(e)
            self._disconnected()

    def playlists_click(self, item=-1, button=1):
        playlist = self.data["list"]["content"][item]
        try:
            # Scrolled left
            if button == -1:
                return ""

            # No click
            if item == -1:
                return "listview"
            # Scroll

            # Normal click: replace and play
            elif button == 1:
                self.load_playlist(playlist, True)
                return ""

            # Long press: same as normal, but stay
            elif button == 2:
                self.load_playlist(playlist, True)
                self.logger.debug("Playlists item longpressed: %s" % item)
                return "listview"

            # Scroll: Activate menu item
            elif button >= 3:
                selection = self.data["list"]["buttons"][button-3]
                if selection["action"]:
                    selection["action"](playlist, False)

                self.logger.debug("Playlists item scrolled: %s" % button)
                return "listview"

        except Exception as e:
            self.logger.error("No playlist %s" % item)

        return ""

    def playlist_click(self, item=-1, button=1):
        try:
            self.logger.debug("List button: %s" % button)

            # Scrolled left
            if button == -1:
                return ""

            # No click
            if item == -1:
                return "listview"

            # Normal click: play
            elif button == 1:
                self.play_item(item)
                return ""

            # Long press: same as normal, but stay
            elif button == 2:
                self.play_item(item)
                self.logger.debug("Playlist item longpressed: %s" % button)
                return "listview"

            # Scroll: Activate menu item and stay
            elif button >= 3:
                selection = self.data["list"]["buttons"][button-3]
                if selection["action"]:
                    selection["action"](item)
                    self.get_playlist()

                self.logger.debug("Playlist item scrolled: %s" % button)
                return "listview"

        except Exception as e:
            self.logger.error(e)
        return ""

    # TODO: Remember previous scroll position when navigating back
    def library_click(self, item=-1, button=1):
        try:
            selected = self.data["list"]["content"][item]

            # Scrolled left
            if button == -1:
                if self.data["list"]["type"] == "title" and self.previouslibraryview["artist"]:
                    self.list_library("album", "artist", self.previouslibraryview["artist"])
                    return "listview"
                elif self.data["list"]["type"] == "album" and self.previouslibraryview["genre"]:
                    self.list_library("artist", "genre", self.previouslibraryview["genre"])
                    return "listview"
                elif self.data["list"]["type"] == "artist":
                    self.list_library("genre")
                    return "listview"
                else:
                    self.previouslibraryview["genre"] = ""
                    self.previouslibraryview["artist"] = ""
                    return ""

            # No click
            elif item == -1:
                return "listview"

            # Normal click: navigate library or add to playlist
            elif button == 1:
                # Last view was genres -> show artists for genre
                if self.data["list"]["type"] == "genre":
                    self.previouslibraryview["genre"] = selected
                    self.list_library("artist", "genre", selected)
                    return "listview"

                # Last view was artists -> show albums for artist
                elif self.data["list"]["type"] == "artist":
                    self.previouslibraryview["artist"] = selected
                    self.list_library("album", "artist", selected)
                    return "listview"

                # Last view was albums -> show songs for album
                elif self.data["list"]["type"] == "album":
                    self.list_library("title", "album", selected)
                    return "listview"

                # Last view was songs -> play item
                elif self.data["list"]["type"] == "title":
                    self.findadd(self.data["list"]["type"], selected, True)
                    return ""

            # Longpress: Replace in playlist and stay
            elif button == 2:
                self.findadd(self.data["list"]["type"], selected, True)
                return "listview"

            # Scroll: Activate menu item and stay
            elif button >= 3:
                selection = self.data["list"]["buttons"][button-3]
                if selection["action"]:
                    selection["action"](self.data["list"]["type"], selected, False)

                self.logger.debug("Library item scrolled: %s" % button)
                return "listview"

        except Exception as e:
            self.logger.error(e)
            return ""

    def fetch_coverart(self, song):
        self.data["cover"] = False
        self.data["coverartfile"]=""

        # Search for local coverart
        if "file" in song and self.config.library_path:

            folder = os.path.dirname(self.config.library_path + "/" + song["file"])
            coverartfile = ""

            # Get all folder.* files from album folder
            coverartfiles = glob.glob(folder + '/folder.*')

            if coverartfiles:
                self.logger.debug("Found coverart files: %s" % coverartfiles)
                # If multiple found, select one of them
                for file in coverartfiles:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        if not coverartfile:
                            coverartfile = file
                            self.logger.debug("Set coverart: %s" % coverartfile)
                        else:
                            # Found multiple files. Assume that the largest one has the best quality
                            if os.path.getsize(coverartfile) < os.path.getsize(file):
                                coverartfile = file
                                self.logger.debug("Better coverart: %s" % coverartfile)
                if coverartfile:
                    # Image found, load it
                    self.logger.debug("Using MPD coverart: %s" % coverartfile)
                    self.data["coverartfile"] = coverartfile
                    self.data["cover"] = True
                    self.data["update"]["coverart"] = True
                else:
                    self.logger.debug("No local coverart file found, switching to Last.FM")

        # No existing coverart, try to fetch from LastFM
        if not self.data["cover"] and self.lfm_connected:

            try:
                lastfm_album = self.lfm.get_album(song["artist"], song["album"])
            except Exception as e:
                self.lfm_connected = False
                lastfm_album = {}
                self.logger.error(e)
                pass

            if lastfm_album:
                try:
                    coverart_url = lastfm_album.get_cover_image(2)
                    if coverart_url:
                        self.data["coverartfile"] = self.config.logpath + "/mpd_cover.png"
                        subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.data["coverartfile"]), shell=True )
                        self.logger.debug("MPD coverart downloaded from Last.fm")
                        self.data["cover"] = True
                        self.data["update"]["coverart"] = True
                except Exception as e:
                    self.logger.error(e)
                    pass

    def connect_lfm(self):
        self.logger.info("Setting Pylast")
        self.lfm_connected = False
        try:
            self.lfm = pylast.LastFMNetwork(api_key = self.config.API_KEY, api_secret = self.config.API_SECRET)
            self.lfm_connected = True
            self.logger.debug("Connected to Last.fm")
        except:
            self.lfm = ""
            time.sleep(5)
            self.logger.debug("Last.fm not connected")