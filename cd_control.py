# -*- coding: utf-8 -*-
import subprocess
from threading import Thread
import time
import DiscID
import CDDB
import pylast

from player_base import PlayerBase

class CDControl (PlayerBase):
    def __init__(self, config):
        super(CDControl, self).__init__("cd", config)

        self.capabilities["connected"]       = True
        self.capabilities["logopath"]        = ""

        # Pylast
        self.lfm_connected = False
        self.connect()

        self.cd_inserted = True
        self.cdinfo = {}

    def refresh(self, active=False):
        status = {}
        song = {}

        # Read new CD
        if self.cd_inserted and not self.cdinfo:
            self.cd_inserted, self.cdinfo = self._read_cd()
            if not self.cd_inserted:
                self.eject()

        try:
            if active and self.cdinfo:
                song["artist"] = self.cdinfo["artist"]
                song["album"]  = self.cdinfo["album"]
                song["date"]   = self.cdinfo["date"]
                song["track"]  = 1
                song["title"]  = self.cdinfo["tracks"][song["track"]]["title"]
                song["time"]   = self.cdinfo["tracks"][song["track"]]["time"]
            else:
                song = {}

            # Sanity check
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

            # Check for changes in song
            if song != self.data["song"]:
                if (
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

    def connect(self):
        # (re)connect to last.fm
        if not self.lfm_connected and self.config.API_KEY and self.config.API_SECRET:
            self.connect_lfm()

    def eject(self):
        self.cd_inserted = False
        self.cdinfo = {}
        self.data["cover"] = False
        self.data["coverartfile"] = ""

    def load_cd(self):
        self.cd_inserted = True
        self.force_update()

    def _read_cd(self):
        inserted = True

        # Open drive
        try:
            cdrom = DiscID.open()
            disc_id = DiscID.disc_id(cdrom)
            self.logger.debug("Loaded new cd, id: %s" % disc_id)
        except Exception as e:
            inserted = False
            self.logger.error(e)
            disc_id = {}

        if disc_id:
            disc_info = self._query_cddb(disc_id)
            cdinfo = self._parse_disc(disc_id, disc_info)
        else:
            cdinfo = {}

        return inserted, cdinfo

    def _query_cddb(self, disc_id):
        try:
            (query_status, query_info) = CDDB.query(disc_id)
            self.logger.debug("CDDB Query status: %s" % query_status)
        except Exception as e:
            self.logger.error(e)
            query_status = 0
            query_info = {}

        # Exact match found
        try:
            if query_status == 200:
                (read_status, read_info) = CDDB.read(query_info["category"], query_info["disc_id"])
                self.logger.debug("CDDB Read Status: %s" % read_status)

            # Multiple matches found - pick first
            elif query_status == 210 or query_status == 211:
                (read_status, read_info) = CDDB.read(query_info[0]["category"], query_info[0]["disc_id"])
                self.logger.debug("CDDB Read Status: %s" % read_status)

            # No match found
            else:
                self.logger.info("CD query failed, status: %s " % query_status)
        except Exception as e:
            self.logger.error(e)
            read_status = 0
            read_info = {}

        if read_status != 210:
            self.logger.info("CDDB read failed, status: %s" % read_status)

        return read_info

    def _parse_disc(self, disc_id, cdinfo):
        disc = {}
        disc["tracks"] = {}
        # Artist
        try:
            disc["artist"] = cdinfo["DTITLE"].split(" / ")[0]
        except:
            disc["artist"] = ""

        # Album
        try:
            disc["album"] = cdinfo["DTITLE"].split(" / ")[1]
        except:
            disc["album"] = ""

        # Date
        try:
            disc["date"] = cdinfo["DYEAR"]
        except:
            disc["date"] = ""

        # Track titles and times
        for track in range(0,disc_id[1]):
            disc["tracks"][track+1] = {}
            try:
                # Title
                disc["tracks"][track+1]["title"] = cdinfo["TTITLE" + str(track)]

                # Time
                if track == disc_id[1]-1:
                    # Final track : CD length in seconds - start frame of final track
                    disc["tracks"][track+1]["time"] = disc_id[track+3] - disc_id[track+2] / 75
                else:
                    # Other tracks: count from start frame of track and next track.
                    disc["tracks"][track+1]["time"] = (disc_id[track+3] - disc_id[track+2]) / 75

            except Exception as e:
                disc["tracks"][track+1]["title"] = ""
                disc["tracks"][track+1]["time"] = ""
                self.logger.error(e)

        # Fetch coverart
        if not self.data["cover"]:
            self.logger.debug("CD coverart changed, fetching...")

            # Find cover art on different thread
            try:
                if self.coverartThread:
                    if not self.coverartThread.is_alive():
                        self.coverartThread = Thread(target=self._fetch_coverart(disc["artist"], disc["album"]))
                        self.coverartThread.start()
                else:
                    self.coverartThread = Thread(target=self._fetch_coverart(disc["artist"], disc["album"]))
                    self.coverartThread.start()
            except Exception as e:
                self.logger.error("Coverartthread: %s" % e)

        return disc

    def _fetch_coverart(self, artist, album):
        self.data["cover"] = False
        self.data["coverartfile"]= ""

        # Try to fetch from LastFM
        if self.lfm_connected:
            try:
                lastfm_album = self.lfm.get_album(artist, album)
            except Exception as e:
                self.lfm_connected = False
                lastfm_album = {}
                self.logger.error(e)
                pass

            if lastfm_album:
                try:
                    coverart_url = lastfm_album.get_cover_image(2)
                    if coverart_url:
                        self.data["coverartfile"] = self.config.logpath + "/cd_cover.png"
                        subprocess.check_output("wget -q %s -O %s" % (coverart_url, self.data["coverartfile"]), shell=True )
                        self.logger.debug("CD coverart downloaded from Last.fm")
                        self.data["cover"] = True
                        self.data["update"]["coverart"] = True
                except Exception as e:
                    self.logger.error(e)
                    pass

    def control(self, command, parameter=-1):
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
            self.logger.error("Last.fm not connected")
