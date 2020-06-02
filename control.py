# -*- coding: utf-8 -*-
import logging
import config
if config.spotify_host and config.spotify_port:
    from spotify_control import SpotifyControl
if config.mpd_host and config.mpd_port:
    from mpd_control import MPDControl
if config.cdda_enabled:
    from cd_control import CDControl

class PlayerControl:
    def __init__(self):
        self.logger  = logging.getLogger("PiTFT-Playerui.player_control")
        self.players = []
        self.current = 0

        # Initialize players
        try:
            self.logger.debug("Setting Spotify")
            if config.spotify_host and config.spotify_port:
                self.players.append(SpotifyControl(config))
        except Exception as e:
            self.logger.error(e)
        try:
            self.logger.debug("Setting MPD")
            if config.mpd_host and config.mpd_port:
                self.players.append(MPDControl(config))
        except Exception as e:
            self.logger.error(e)
        try:
            self.logger.debug("Setting CD")
            if config.cdda_enabled:
                self.players.append(CDControl(config))
        except Exception as e:
            self.logger.error(e)

        # Quit if no players
        if not len(self.players):
            self.logger.error("No players defined! Quitting")
            raise

        # Force first refresh for all players
        self.do_first_refresh = True

    def __getitem__(self, item):
        if self.players[self.current]:
            return self.players[self.current][item]
        else:
            return {}

    def __call__(self, item):
        return self.players[self.current](item)

    def get_players(self):
        return self.players

    def get_current(self):
        return self.current

    def determine_active_player(self):
        active = -1
        # Find changes in activity
        for id, player in enumerate(self.players):
            if player["update"]["active"]:
                active = id
                self.logger.debug("Player %s started: %s" % (id, player("name")))
                self.switch_active_player(id)

        # Player started: pause the rest
        if active != -1:
            for id, player in enumerate(self.players):
                if id != active:
                    if player["status"]["state"] == "play":
                        self.logger.debug("pausing %s" % player("name"))
                        self.control_player("pause", 0, id)

    def refresh(self):
        active = False
        # Update all for active, only status for rest
        for id, player in enumerate(self.players):
            try:
                player.refresh(self.current == id or self.do_first_refresh)
                self.do_first_refresh = False
            except Exception as e:
                self.logger.error(e)

        # Get active player
        self.determine_active_player()

        # Return true if playing
        if self.players[self.current]["status"]["state"] == "play":
            active = True
        return active, self.updated()
        
    def updated(self, item="all"):
        if item == "all":
            return True in self.players[self.current]["update"].values()
        else:
            return self.players[self.current]["update"][item]

    def update_ack(self, item):
        self.players[self.current].update_ack(item)

    def control_player(self, command, parameter=-1, id=-1):
        # Translate
        if self.players[self.current]["status"]:
            if command == "play_pause":
                if self.players[self.current]["status"]["state"] == "play":
                    command = "pause"
                else:
                    command = "play"

        # Switching commands
        if command == "switch":
            self.switch_active_player(parameter)

        # Player specific commands
        elif id != -1:
            self.players[id].control(command, parameter)
        # ID not specified
        else:
            self.players[self.current].control(command, parameter)

    def switch_active_player(self, id):
        player_changed = False

        # Name provided: find id
        if isinstance(id, basestring):
            for number, player in enumerate(self.get_players()):
                if id == player("name"):
                    id = number

        # ID exists: perform the switch
        if id != -1:
            if self.current != id:
                player_changed = True
                self.current = id
                self.logger.debug("Switching player to %s" % self.players[id]("name"))

            # Player changed, refresh data
            if player_changed:
                self.players[self.current].force_update()
            # Ack the request
            self.players[self.current].update_ack("active")

    def get_active_player(self):
        return self.current
