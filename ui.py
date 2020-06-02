#!/usr/bin/python2
# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import os
import subprocess
import logging
import datetime
from math import ceil, floor
from datetime import timedelta
from signal import alarm, signal, SIGALRM, SIGTERM, SIGKILL
from logging.handlers import TimedRotatingFileHandler
from daemon import Daemon

# Own modules
from control import PlayerControl
from screen_manager import ScreenManager
import config

# Additional modules, if in config
if config.lircrcfile:
    import lirc

# OS enviroment variables for pitft
#os.putenv ("SDL_VIDEODRIVER" , "fbcon")
os.environ["SDL_FBDEV"] = "/dev/fb1"
os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
os.environ["SDL_MOUSEDRV"] = "TSLIB"

# Logger config
if not os.path.isdir (config.logpath):
    os.mkdir(config.logpath)

path = os.path.dirname(os.path.abspath(__file__)) + "/"

logger = logging.getLogger("PiTFT-Playerui")
try:
    if config.loglevel == "DEBUG":
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)-5s %(name)-32s %(lineno)-4d %(message)s")
    else:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
except:
    logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(config.logpath + '/pitft-playerui.log',when="midnight",interval=1,backupCount=14)
handler.setFormatter(formatter)
logger.addHandler(handler)

## HAX FOR FREEZING ##
class Alarm(Exception):
    pass
def alarm_handler(signum, frame):
    logger.debug("ALARM")
    raise Alarm
## HAX END ##

def signal_term_handler(signal, frame):
    logger.debug('got SIGTERM')
    sys.exit(0)

class PitftDaemon(Daemon):

    # Setup Python game and Screen manager
    def setup(self):
        logger.info("Starting setup")

        signal(SIGTERM, signal_term_handler)
        # Python game ######################
        logger.info("Setting pygame")
        pygame_init_done = False
        while not pygame_init_done:
            try:
                pygame.init()
                pygame_init_done = True
            except:
                logger.debug("Pygame init failed")
                pygame_init_done = False
                time.sleep(5)

        pygame.mouse.set_visible(False)

        # Hax for freezing
        signal(SIGALRM, alarm_handler)
        alarm(1)
        try:
            # Set screen size
            size = width, height = config.resolution
            self.screen = pygame.display.set_mode(size)
            alarm(0)
        except Alarm:
            logger.debug("Keyboard interrupt?")
            raise KeyboardInterrupt
        # Hax end

        logger.info("Display driver: %s" % pygame.display.get_driver())

        # Player control ###############
        logger.info("Setting player control")
        self.pc = PlayerControl()
        logger.debug("Player control set")

        # Screen manager ###############
        logger.info("Setting screen manager")
        self.sm = ScreenManager(path, self.pc)
        logger.debug("Screen manager set")

        # LIRC
        lircrcfile = path + config.lircrcfile
        self.lirc_enabled = False
        if os.path.isfile(lircrcfile):
            try:
                self.lirc_sockid = lirc.init("pitft-playerui", lircrcfile, blocking=False)
                self.lirc_enabled = True
            except Exception as e:
                logger.error(e)
                self.lirc_enabled = False

        # Mouse variables
        self.clicktime          = datetime.datetime.now()
        self.longpress_time     = timedelta(milliseconds=300)
        self.click_filtertime   = datetime.datetime.now()
        self.click_filterdelta  = timedelta(milliseconds=10)
        self.scroll_threshold   = (20, 20)
        self.start_pos          = 0,0
        self.mouse_scroll       = ""
        self.mousebutton_down   = False
        self.pos                = 0

        # Smooth scrolling variables
        self.smoothscroll           = False
        self.smoothscroll_direction = 0,0
        self.smoothscroll_directions_index = 0
        self.smoothscroll_direction_samples = 10
        self.smoothscroll_directions = [0]*self.smoothscroll_direction_samples
        self.smoothscroll_factor    = 0.9
        self.smoothscroll_timedelta = timedelta(milliseconds=1)
        self.smoothscroll_time      = datetime.datetime.now()

        # Times in milliseconds
        self.screen_refreshtime = 16.67
        self.player_refreshtime = 200

        #Backlight
        self.screen_timer = 0.0
        self.backlight = False
        self.update_screen_timeout(True)
        logger.debug("Setup done")

    def shutdown(self):
        pass
            
    # Main loop
    def run(self):
        self.setup()
        drawtime = datetime.datetime.now()
        refreshtime = datetime.datetime.now()

        while 1:
            updated = False
            
            # Check mouse and LIRC events
            try:
                active = self.read_mouse()
                if self.lirc_enabled:
                    active = active | self.read_lirc()
            except Exception as e:
                logger.error(e)

            try:
                # Refresh info
                if refreshtime < datetime.datetime.now():
                    refreshtime = datetime.datetime.now() + timedelta(milliseconds=self.player_refreshtime)

                    # Refresh information from players
                    ret, updated = self.pc.refresh()
                    active = active | ret

                    # Update screen
                    if updated:
                        self.sm.refresh()
            except Exception as e:
                logger.error(e)

            try:
                # Update screen timeout, if there was any activity
                if config.screen_timeout > 0:
                    self.update_screen_timeout(active)
            except Exception as e:
                logger.error(e)

            try:
                # Draw screen
                if drawtime < datetime.datetime.now():
                    drawtime = datetime.datetime.now() + timedelta(milliseconds=self.screen_refreshtime)

                    # Don't draw when display is off
                    if self.backlight:
                        self.sm.render(self.screen)
                        pygame.display.flip()
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.error(e)

    def read_mouse(self):
        direction = 0,0
        userevents = False

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.clicktime = datetime.datetime.now()
                # Filter out if instantly after previous mousebutton up event
                if self.clicktime > self.click_filtertime:
                    self.pos = self.start_pos = pygame.mouse.get_pos()
                    userevents = True
                    if event.button == 1:
                        if self.smoothscroll:
                            self.scroll(self.start_pos, (0,0), True)
                            self.smoothscroll = False
                            self.smoothscroll_directions_index = 0
                            self.smoothscroll_directions = [0]*self.smoothscroll_direction_samples
                            self.smoothscroll_direction = 0,0

                        # Instant click when backlight is off to wake
                        if not self.backlight:
                            self.mousebutton_down = False
                        else:
                            self.mousebutton_down = True

                    # Scroll wheel
                    elif event.button == 4:
                        self.scroll(self.start_pos, (0,30), True)
                    elif event.button == 5:
                        self.scroll(self.start_pos, (0,-30), True)

            elif event.type == pygame.MOUSEMOTION and self.mousebutton_down:
                userevents = True
                pos = pygame.mouse.get_pos()
                direction = (pos[0] - self.pos[0], pos[1] - self.pos[1])

                if not self.mouse_scroll:
                    # Start scrolling: Lock direction
                    if abs(direction[0]) >= self.scroll_threshold[0]:
                        self.mouse_scroll = "x"

                    elif abs(direction[1]) >= self.scroll_threshold[1]:
                        self.mouse_scroll = "y"

                # Scrolling already, update offset
                if self.mouse_scroll == "x":
                    direction = direction[0], 0
                elif self.mouse_scroll == "y":
                    direction = 0, direction[1]
                else:
                    direction = 0, 0

                if self.mouse_scroll:
                    self.smoothscroll = self.scroll(self.start_pos, direction)

                # Save directions from latest samples for smooth scrolling - Direction is always Y
                self.smoothscroll_directions_index = self.smoothscroll_directions_index + 1 
                if self.smoothscroll_directions_index > self.smoothscroll_direction_samples-1:
                    self.smoothscroll_directions_index = 0

                self.smoothscroll_directions[self.smoothscroll_directions_index] = direction[1]
                self.smoothscroll_direction = 0, sum(self.smoothscroll_directions)

                # Save new position
                self.pos = pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                userevents = True
                if self.mousebutton_down:
                    # Not a long click or scroll: click
                    if not self.mouse_scroll:
                        self.click(1, self.start_pos)
                    # Scrolling: End right away or start deceleration if allowed
                    else:
                        if self.smoothscroll:
                            self.scroll(self.start_pos, self.smoothscroll_direction)
                            self.smoothscroll_time = datetime.datetime.now() + self.smoothscroll_timedelta
                        else:
                            self.scroll(self.start_pos, (0,0), True)
                            self.mouse_scroll = ""

                # Clear variables
                self.mousebutton_down = False

                # Filter next click, if it happens instantly
                self.click_filtertime = datetime.datetime.now() + self.click_filterdelta

        # Long press - register second click
        if self.mousebutton_down and not self.mouse_scroll and not self.smoothscroll:
            userevents = True
            if datetime.datetime.now() - self.clicktime > self.longpress_time:
                self.mousebutton_down = self.click(2, self.start_pos)

                # Update timers
                self.clicktime = datetime.datetime.now()

        # No activity, but smooth scrolling
        if self.smoothscroll and not self.mousebutton_down:
            if datetime.datetime.now() > self.smoothscroll_time:
                userevents = True
                self.smoothscroll_direction = 0, int(self.smoothscroll_direction[1] * self.smoothscroll_factor)

                # Decelerated under threshold -> Stop scrolling
                if abs(self.smoothscroll_direction[1]) < self.scroll_threshold[1]:
                    self.scroll(self.start_pos, (0,0), True)
                    self.mouse_scroll = ""
                    self.smoothscroll = False
                    self.smoothscroll_directions_index = 0
                    self.smoothscroll_directions = [0]*self.smoothscroll_direction_samples
                    self.smoothscroll_direction = 0,0

                else: # Continue scrolling
                    self.scroll(self.start_pos, self.smoothscroll_direction)
                    self.smoothscroll_time = datetime.datetime.now() + self.smoothscroll_timedelta

        return userevents

    def click(self, mousebutton, clickpos):
        self.sm.click(mousebutton, clickpos)

    def scroll(self, start, direction, end=False):
        return self.sm.scroll(start, direction, end)

    def read_lirc(self):
        commands = lirc.nextcode()
        if commands:
            for line in commands:
                logger.debug("LIRC: %s" % line)
                try:
                    target, command = line.split()
                    if target == "switch":
                        self.sm.switch_player(command)
                    elif target == "control":
                        self.pc.control_player(command)
                    else:
                        logger.debug("LIRC: Unknown target %s" % target)
                except Exception as e:
                    logger.error(e)
            return True
        return False

    def set_backlight(self, state):
        logger.debug("Backlight %s" %state)
        subprocess.call("echo '" + str(state*1) + "' > " + config.backlight_sysfs, shell=True)
        self.backlight = state

    def update_screen_timeout(self, active):
        if active:
            self.screen_timer = datetime.datetime.now() + timedelta(seconds=config.screen_timeout)
            if not self.backlight:
                self.set_backlight(True)
        elif self.screen_timer < datetime.datetime.now() and self.backlight:
            self.set_backlight(False)

if __name__ == "__main__":
    daemon = PitftDaemon('/tmp/pitft-playerui-daemon.pid')
    if len(sys.argv) > 1:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.shutdown()
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print ("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print ("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
