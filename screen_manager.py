# -*- coding: utf-8 -*-
import sys, pygame
from pygame.locals import *
import time
import logging
import os
from math import ceil, floor

import config
from positioning import *

class ScreenManager:
    def __init__(self, path, pc):
        self.logger = logging.getLogger("PiTFT-Playerui.screen_manager")
        os.chdir(path)
        self.pc = pc

        # Fonts
        try:
            self.font = {}
            self.font["menuitem"]    = pygame.font.Font(config.fontfile, 20)
            self.font["details"]     = pygame.font.Font(config.fontfile, 16)
            self.font["elapsed"]     = pygame.font.Font(config.fontfile, 16)
            self.font["listview"]    = pygame.font.Font(config.fontfile, 20)
        except Exception as e:
            self.logger.error(e)
            raise

        # Images
        try:
            self.image = {}
            self.image["background"]             = pygame.image.load("pics/" + "background.png")

            self.image["coverart_place"]         = pygame.image.load("pics/" + "coverart-placer.png")
            self.image["coverart_border_clean"]  = pygame.image.load("pics/" + "coverart-border.png")
            self.image["coverart_border_paused"] = pygame.image.load("pics/" + "coverart-paused.png")
            self.image["coverart_border_next"]   = pygame.image.load("pics/" + "coverart-next.png")
            self.image["coverart_border_prev"]   = pygame.image.load("pics/" + "coverart-previous.png")

            self.image["cover"]                  = self.image["coverart_place"]
            self.image["coverart_border"]        = self.image["coverart_border_clean"]

            self.image["progress_bg"]            = pygame.image.load("pics/" + "position-background.png")
            self.image["progress_fg"]            = pygame.image.load("pics/" + "position-foreground.png")
            self.image["volume_bg"]              = pygame.image.load("pics/" + "volume_bg.png")
            self.image["volume_fg"]              = pygame.image.load("pics/" + "volume_fg.png")
            self.image["scroll_bg"]              = pygame.transform.scale(self.image["volume_bg"], size["scrollbar"])
            self.image["scroll_fg"]              = self.image["volume_fg"]

            self.image["button_repeat_off"]      = pygame.image.load("pics/" + "button-repeat-off.png")
            self.image["button_repeat_on"]       = pygame.image.load("pics/" + "button-repeat-on.png")
            self.image["button_repeat"]          = self.image["button_repeat_off"]
            self.image["button_random_off"]      = pygame.image.load("pics/" + "button-random-off.png")
            self.image["button_random_on"]       = pygame.image.load("pics/" + "button-random-on.png")
            self.image["button_random"]          = self.image["button_repeat_off"]

        except Exception as e:
            self.logger.error(e)
            raise

        # Things to show
        self.status = {}
        self.status["artist"]          = ""
        self.status["album"]           = ""
        self.status["artistalbum"]     = ""
        self.status["date"]            = ""
        self.status["track"]           = ""
        self.status["title"]           = ""
        self.status["file"]            = ""
        self.status["timeElapsed"]     = "00:00"
        self.status["timeTotal"]       = "00:00"
        self.status["timeElapsedPercentage"] = 0
        self.status["playbackStatus"]  = "stop"
        self.status["volume"]          = 0
        self.status["random"]          = False
        self.status["repeat"]          = False

        self.status["update"] = {}
        self.status["update"]["screen"]    = True
        self.status["update"]["state"]     = True
        self.status["update"]["elapsed"]   = True
        self.status["update"]["random"]    = True
        self.status["update"]["repeat"]    = True
        self.status["update"]["volume"]    = True
        self.status["update"]["trackinfo"] = True
        self.status["update"]["coverart"]  = True

        # Visual indicators when scrolling on sliders
        self.seekpos = -1.0
        self.volumepos = -1

        self.view = "main"
        self.scroll_start       = -1,-1
        self.scroll_threshold   = 40
        self.scroll_offset      = 0,0
        self.list_scroll_threshold = 40
        self.draw_offset        = 0,0
        self.list_offset        = 0
        self.listitems_on_screen = config.resolution[1]//size["listitem_height"]

        self.populate_players()

    def populate_players(self):
        self.topmenu = self.pc.get_players()
        for player in self.topmenu:
            # Load player logo
            try:
                logopath = player('logopath')
                if logopath:
                    player.set_logo(pygame.transform.scale(pygame.image.load(logopath), size["logo"]))
                else:
                    player.set_logo(None)
            except Exception as e:
                self.logger.error(e)
                
            # Load list button icons
            try:
                listbuttons = player('listbuttons')
                if listbuttons:
                    for name, button in listbuttons.items():
                        player.set_buttonicon(name, pygame.transform.scale(pygame.image.load(button["path"]), size["listbutton"]))
            except Exception as e:
                self.logger.error(e)

    def refresh(self):
        updated = False
        # Parse new song information
        try:
            self.parse_song()
        except Exception as e:
            self.logger.error(e)
            pass
            
        return self.updated()

    def parse_song(self):

        # State icons on cover art
        if self.pc.updated("state"):
            if self.pc["status"]["state"] == "play":
                self.image["coverart_border"] = self.image["coverart_border_clean"]
            else:
                self.image["coverart_border"] = self.image["coverart_border_paused"]

            self.force_update("state")
            self.force_update("coverart")
            self.pc.update_ack("state")

        if self.pc.updated("elapsed"):

            # Time elapsed
            try:
                min = int(ceil(float(self.pc["status"]["elapsed"])))/60
                min = min if min > 9 else "0%s" % min
                sec = int(ceil(float(self.pc["status"]["elapsed"])%60))
                sec = sec if sec > 9 else "0%s" % sec
                self.status["timeElapsed"] = "%s:%s" % (min,sec)
            except:
                self.status["timeElapsed"] = ""

            # Time elapsed percentage
            try:
                self.status["timeElapsedPercentage"] = float(self.pc["status"]["elapsed"])/float(self.pc["song"]["time"])
            except:
                self.status["timeElapsedPercentage"] = 0

            self.force_update("elapsed")
            self.pc.update_ack("elapsed")

        if self.pc.updated("trackinfo"):

            # Position
            try:
                self.status["pos"] = self.pc["song"]["pos"]
            except:
                self.status["pos"] = ""

            try:
                self.status["artist"] = self.pc["song"]["artist"].decode('utf-8')
            except:
                self.status["artist"] = ""

            # Album
            try:
                self.status["album"] = self.pc["song"]["album"].decode('utf-8')
            except:
                self.status["album"] = ""

            # Artist - Album
            if self.status["artist"]:
                self.status["artistalbum"] = self.status["artist"]
                if self.status["album"]:
                    self.status["artistalbum"] += " - "
            else:
                self.status["artistalbum"] = ""
            self.status["artistalbum"] += self.status["album"]

            # Date
            try:
                self.status["date"] = self.pc["song"]["date"].decode('utf-8')
            except:
                self.status["date"] = ""

            # Append: Artist - Album (date)
            if self.status["date"]:
                self.status["artistalbum"] += " (" + self.status["date"] + ")"

            # Track number
            try:
                self.status["track"] = self.pc["song"]["track"].decode('utf-8')
            except:
                self.status["track"] = ""

            # Title
            try:
                if self.pc["song"]["title"]:
                    self.status["title"] = self.pc["song"]["title"].decode('utf-8')
                else:
                    self.status["title"] = self.pc["song"]["file"].decode('utf-8')
            except:
                self.status["title"] = ""

            if self.status["track"]:
                self.status["title"] = self.status["track"] + " - " + self.status["title"]

            # Time total
            try:
                min = int(ceil(float(self.pc["song"]["time"])))/60
                sec = int(ceil(float(self.pc["song"]["time"])%60))
                min = min if min > 9 else "0%s" % min
                sec = sec if sec > 9 else "0%s" % sec
                self.status["timeTotal"] = "%s:%s" % (min,sec)
            except:
                self.status["timeTotal"] = ""

            self.force_update("trackinfo")
            self.pc.update_ack("trackinfo")

        if self.pc.updated("random"):
            try:
                self.status["random"] = int(self.pc["status"]["random"])
            except:
                self.status["random"] = False

            if self.status["random"]:
                self.image["button_random"] = self.image["button_random_on"]
            else:
                self.image["button_random"] = self.image["button_random_off"]

            self.force_update("random")
            self.pc.update_ack("random")

        if self.pc.updated("repeat"):
            try:
                self.status["repeat"] = int(self.pc["status"]["repeat"])
            except:
                self.status["repeat"] = False
            if self.status["repeat"]:
                self.image["button_repeat"] = self.image["button_repeat_on"]
            else:
                self.image["button_repeat"] = self.image["button_repeat_off"]

            self.force_update("repeat")
            self.pc.update_ack("repeat")

        if self.pc.updated("volume"):
            try:
                self.status["volume"] = int(self.pc["status"]["volume"])
            except:
                self.status["volume"] = 0

            self.force_update("volume")
            self.pc.update_ack("volume")

        if self.pc.updated("coverart"):
            self.image["cover"] = self.fetch_coverart(self.pc["coverartfile"])

            self.force_update("coverart")
            self.pc.update_ack("coverart")

    def fetch_coverart(self, coverartfile):
        if coverartfile:
            try:
                self.logger.debug("Using coverart: %s" % coverartfile)
                coverart = pygame.image.load(coverartfile)
                return pygame.transform.scale(coverart, size["coverart"])
            except Exception as e:
                self.logger.error(e)
                return self.image["coverart_place"]
        else:
            return self.image["coverart_place"]

    def render(self, surface):
        if self.updated("screen"):
            surface.blit(self.image["background"], (0,0))
        try:
            if self.view == "main":
                self.render_mainscreen(surface)
            elif self.view == "listview":
                self.render_listview(surface)
        except Exception as e:
            self.logger.error(e)
            pass

    def click(self, mousebutton, clickpos):
        try:
#            self.logger.debug("Click: " + str(mousebutton) + " X: " + str(clickpos[0]) + " Y: " + str(clickpos[1]))
            if self.view == "main":
                allow_repeat = self.click_mainscreen(mousebutton, clickpos)
            elif self.view == "listview":
                allow_repeat = self.click_listview(mousebutton, clickpos)
        except Exception as e:
            self.logger.error(e)
            allow_repeat = False
            pass
        return allow_repeat

    def scroll(self, start, direction, end=False):
        # Update total offset
        self.scroll_offset = (self.scroll_offset[0] + direction[0], self.scroll_offset[1] + direction[1])

        # Screen specific
        if self.view == "main":
            allow_smoothscroll = self.scroll_mainscreen(start, self.scroll_offset, end)
        elif self.view == "listview":
            allow_smoothscroll = self.scroll_listview(start, self.scroll_offset, end)

        if end:
            self.scroll_offset = 0,0

        # Redraw screen
        self.force_update("screen")

        return allow_smoothscroll

    def switch_view(self, view):
        if view == "main":
            self.view=view
        elif view == "listview":
            # Center currently playing item
            self.list_offset = (self.pc["list"]["position"]-self.listitems_on_screen/2)*size['listitem_height']
            self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, size["listitem_height"]*(len(self.pc["list"]["viewcontent"])-self.listitems_on_screen-1)))[1]
            if self.pc["list"]["viewcontent"] and self.pc["list"]["click"]:
                self.view=view
        else:
            self.logger.debug("Unknown view %s" % view)
        self.force_update()

    def switch_player(self, id):
        self.pc.control_player("switch", id)
        self.force_update()

    def render_mainscreen(self,surface):
        if self.updated("screen"):
            # Update everything
            self.force_update()

            # Bottom menu
            for index, item in enumerate(self.pc["menu"]):
                color = "text" if self.draw_offset[1] == -(index+1)*size["bottommenu"] else "inactive"
                text = render_text(item["name"], self.font["menuitem"], color)
                text_rect = text.get_rect(center=(config.resolution[0]/2, 0))
                surface.blit(text,
                            menupos("bottommenu", index, (text_rect[0],self.draw_offset[1])))
            # Top menu
            for i in range (0,len(self.topmenu)-1):
                index = i if i < self.pc.get_current() else i+1
                color = "text" if self.draw_offset[1] == (i+1)*size["topmenu"] else "inactive"
                text = render_text(self.topmenu[index]("name").upper(), self.font["menuitem"], color)
                text_rect = text.get_rect(center=(config.resolution[0]/2, 0))
                surface.blit(text,
                            menupos("topmenu", i, (text_rect[0],self.draw_offset[1]), "up"))
            self.update_ack("screen")

        # Track info
        if self.updated("trackinfo"):
            # Refresh backgrounds
            surface.blit(self.image["background"],
                        pos("trackinfobackground",(0, self.draw_offset[1])),
                        (pos("trackinfobackground",(0, self.draw_offset[1])),
                        size["trackinfobackground"]))
            surface.blit(self.image["progress_bg"],
                        pos("progressbar", (0, self.draw_offset[1])))

            # Artist - Album (date)
            surface.blit(render_text(self.status["artistalbum"], self.font["details"]),
                        pos("album", (0, self.draw_offset[1])))

            # Track number - title
            surface.blit(render_text(self.status["title"], self.font["details"]),
                        pos("track", (0, self.draw_offset[1])))

            # Total time
            if self.status["timeElapsed"] and self.status["timeTotal"]:

                surface.blit(render_text(self.status["timeTotal"], self.font["elapsed"]),
                            pos("track_length", (0, self.draw_offset[1])))

            # Draw player logo if it exists
            logo = self.pc("logo")
            if logo:
                surface.blit(self.image["background"],
                             pos("logoback",(0, self.draw_offset[1])),
                            (pos("logoback",(0, self.draw_offset[1])),
                            size["logoback"]))
                surface.blit(logo, pos("logo",(0, self.draw_offset[1])))

            self.update_ack("trackinfo")

        # Time Elapsed
        if self.updated("elapsed") and self.pc("elapsed_enabled"):

            # Refresh backgrounds
            surface.blit(self.image["background"],
                         pos("progressbackground",(0, self.draw_offset[1])),
                        (pos("progressbackground",(0, self.draw_offset[1])), size["progressbackground"]))
            surface.blit(self.image["progress_bg"],
                         pos("progressbar", (0, self.draw_offset[1])))

            # Progress bar
            if self.seekpos == -1:
                progress = self.status["timeElapsedPercentage"]
            else:
                progress = self.seekpos
            surface.blit(self.image["progress_fg"],
                        pos("progressbar", (0, self.draw_offset[1])),
                        (0,0,int(size["progressbar"][0]*progress),10))
            # Text
            surface.blit(render_text(self.status["timeElapsed"], self.font["elapsed"]),
                        pos("elapsed", (0, self.draw_offset[1])))

            self.update_ack("elapsed")

        # Buttons
        if self.updated("repeat") and self.pc("repeat_enabled"):
            surface.blit(self.image["button_repeat"],
                        pos("repeatbutton", (self.draw_offset)))
            self.update_ack("repeat")

        if self.updated("random") and self.pc("random_enabled"):
            surface.blit(self.image["button_random"],
                        pos("randombutton", (self.draw_offset)))
            self.update_ack("random")

        #Volume
        if config.volume_enabled and self.updated("volume") and self.pc("volume_enabled"):
            surface.blit(self.image["volume_bg"],
                        pos("volume", (self.draw_offset)))
            # Slider
            pos_volumefg = pos("volume_slider", (self.draw_offset))
            if self.volumepos == -1:
                volumefg_scale = (self.status["volume"]*(size["volume_slider"][1])/100)
            else:
                volumefg_scale = (self.volumepos * (size["volume_slider"][1])/100)

            pos_volumefg = (pos_volumefg[0], pos_volumefg[1]+size["volume_slider"][1]-volumefg_scale)
            surface.blit(self.image["volume_fg"],
                        (pos_volumefg))
            self.update_ack("volume")

        # Cover art
        if self.updated("coverart"):
            surface.blit(self.image["cover"],
                        pos("coverart", self.draw_offset))
            surface.blit(self.image["coverart_border"],
                        pos("coverart", self.draw_offset))
            self.update_ack("coverart")

    def click_mainscreen(self, mousebutton, clickpos):

        allow_repeat = False

        # Coverart clicked - play/pause
        if clicked(clickpos, pos("coverart"), size["coverart"]):
            if mousebutton == 1:
                self.logger.debug("Toggle play/pause")
                self.pc.control_player("play_pause")

        # Repeat button
        if clicked(clickpos, pos("repeatbutton"), size["controlbutton"]) and self.pc("repeat_enabled"):
            self.pc.control_player("repeat")
        if clicked(clickpos, pos("randombutton"), size["controlbutton"]) and self.pc("random_enabled"):
            self.pc.control_player("random")

        # Volume
        if config.volume_enabled and self.pc("volume_enabled") and clicked(clickpos, pos("volume_click"), size["volume_click"]):
            volume = (pos("volume_slider")[1]+size["volume_slider"][1]-clickpos[1])*100/size["volume_slider"][1]
            volume = limit(volume,0,100)
            self.pc.control_player("volume", volume)

        # Progress bar
        if self.pc("elapsed_enabled") and self.pc("seek_enabled"):
            if clicked(clickpos, pos("progressbar"), size["progressbar_click"]) or clicked(clickpos, pos("elapsed"), size["elapsed"]):
                seek = float(clickpos[0]-pos("progressbar")[0])/float(size["progressbar"][0])
                seek = limit(seek,0.0,1.0)
                self.pc.control_player("seek", seek)

        # Return value: allow repeat
        return allow_repeat

    def scroll_mainscreen(self, start, direction, end=False):
        x, y = direction
        allow_smoothscroll = False

        # scrolling progress bar
        if self.pc("seek_enabled") and \
                  (clicked(start, pos("progressbar"), size["progressbar_click"]) or \
                   clicked(start, pos("elapsed"), size["elapsed"])) and \
                   abs(x) > 0:
            self.seekpos = float(start[0]+x-pos("progressbar")[0])/float(size["progressbar"][0])
            self.seekpos = limit(self.seekpos,0.0,1.0)
            if end:
                self.pc.control_player("seek", self.seekpos)
                self.seekpos = -1.0

        # scrolling volume
        elif config.volume_enabled and self.pc("volume_enabled") and \
                   clicked(start, pos("volume_click"), size["volume_click"]) and \
                   abs(y) > 0:
            self.volumepos = (pos("volume_slider")[1]+size["volume_slider"][1]-(start[1]+y))*100/size["volume_slider"][1]
            self.volumepos = limit(self.volumepos,0,100)
            if end:
                self.pc.control_player("volume", self.volumepos)
                self.volumepos = -1

        # Normal scroll
        else:

            # Scroll min/max limits
            x = 0 if abs(x) < self.scroll_threshold else x

            # Menus
            if y > 0:
                y = 0 if y < size["topmenu"] else y-y%size["topmenu"]
            else:
                y = 0 if abs(y) < size["bottommenu"] else y-y%size["bottommenu"]+size["bottommenu"]
            if config.invert_next_prev:
                self.draw_offset = limit_offset((x,y),(-108, -len(self.pc["menu"])*size["bottommenu"],
                                                         108, (len(self.topmenu)-1)*size["topmenu"]))
            else:
                self.draw_offset = limit_offset((-x,y),(-108, -len(self.pc["menu"])*size["bottommenu"],
                                                        108, (len(self.topmenu)-1)*size["topmenu"]))

            # Prev/next
            if x > 0:
                if config.invert_next_prev:
                    self.image["coverart_border"] = self.image["coverart_border_next"]
                else:
                    self.image["coverart_border"] = self.image["coverart_border_prev"]
            elif x < 0:
                if config.invert_next_prev:
                    self.image["coverart_border"] = self.image["coverart_border_prev"]
                else:
                    self.image["coverart_border"] = self.image["coverart_border_next"]
            else:
                if self.pc["status"]["state"] == "play":
                    self.image["coverart_border"] = self.image["coverart_border_clean"]
                else:
                    self.image["coverart_border"] = self.image["coverart_border_paused"]

            if end:
                # Flip: next/prev
                if self.draw_offset[0] > 0:
                    self.pc.control_player("next")
                elif self.draw_offset[0] < 0:
                    self.pc.control_player("previous")

                # Top menu: Player selection
                for i in range (0,len(self.topmenu)-1):
                    index = i if i < self.pc.get_current() else i+1

                    if self.draw_offset[1] == (i+1)*size["topmenu"]:
                        self.switch_player(index)

                i = -self.draw_offset[1]//size["bottommenu"] - 1

                # Scroll limited to list length, but still check for fun
                if i > -1 and len(self.pc["menu"]) >= i:

                    # Only menu item type for now is a list, but more might come
                    if self.pc["menu"][i]["type"] == "listview":
                        # Get list content from player
                        self.pc["menu"][i]['listcontent']()
                        self.switch_view("listview")

                # Reset offset
                self.draw_offset = (0,0)
                # Reset cover image
                if self.pc["status"]["state"] == "play":
                    self.image["coverart_border"] = self.image["coverart_border_clean"]
                else:
                    self.image["coverart_border"] = self.image["coverart_border_paused"]
        return allow_smoothscroll

    def render_listview(self,surface):

        list_draw_offset = self.list_offset%size['listitem_height']
        # Detect scrolling:
        if self.scroll_start[1] > -1:
            scrolled_item = (self.scroll_start[1] + self.list_offset)//size["listitem_height"]
            if scrolled_item > len(self.pc["list"]["viewcontent"])-1:
                scrolled_item = -1
        else:
            scrolled_item = -1
            

        # List content
        if self.pc["list"]["viewcontent"]:
            list_length = len(self.pc["list"]["viewcontent"])
            for i in range(-10*self.listitems_on_screen,11*self.listitems_on_screen):
                list_index = i+self.list_offset//size['listitem_height']
                if list_index in range(0, list_length):
                    try:
                        listitem = self.pc["list"]["viewcontent"][list_index].decode('utf-8')

                    except Exception as e:
                        listitem = ""
                        self.logger.error(e)

                    # Highlight currently playing item
                    if list_index == self.pc["list"]["highlight"]:
                        text = render_text(listitem, self.font["listview"], "highlight")
                    else:
                        text = render_text(listitem, self.font["listview"], "text")

                    # Scroll all left (close), only item right (menu function)
                    if list_index != scrolled_item and self.draw_offset[0] > 0:
                        surface.blit(text, pos("listview", (0,self.draw_offset[1]-list_draw_offset+size['listitem_height']*i)))
                    else:
                        surface.blit(text, pos("listview", (self.draw_offset[0],self.draw_offset[1]-list_draw_offset+size['listitem_height']*i)))

                    # List button icons
                    for index, item in enumerate(self.pc["list"]["buttons"]):
                        if self.draw_offset[0] == self.list_scroll_threshold*(index+1):
                            surface.blit(item["icon"],pos("listview", (12, size['listitem_height']*scrolled_item-self.list_offset)))


            # Scrollbar
            if list_length > self.listitems_on_screen:
                surface.blit(self.image["scroll_bg"],
                             pos("scrollbar", (0, 0)))

                pos_scrollfg = pos("scrollbar_slider")
                scroll_ratio = float(self.list_offset - self.draw_offset[1])
                scroll_ratio = scroll_ratio/float((len(self.pc["list"]["viewcontent"])-self.listitems_on_screen)*size["listitem_height"])
                scroll_ratio = 1.0 if scroll_ratio > 1.0 else scroll_ratio
                scroll_ratio = 0.0 if scroll_ratio < 0.0 else scroll_ratio
                scrollfg_scale = scroll_ratio*float(size["scrollbar_slider"][1])
                pos_scrollfg = (pos_scrollfg[0], pos_scrollfg[1]+scrollfg_scale)
                surface.blit(self.image["scroll_fg"],
                            (pos_scrollfg))
        else:
            self.switch_view("main")

    def click_listview(self, mousebutton, clickpos):

        if clicked(clickpos, pos("scrollbar_click"), size["scrollbar_click"]):
            ratio = float(-32.0 + clickpos[1])*1.20
            ratio = ratio/float(config.resolution[1])
            self.list_offset = int(ratio*size["listitem_height"]*(len(self.pc["list"]["viewcontent"])-1))
            self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, size["listitem_height"]*(len(self.pc["list"]["viewcontent"])-self.listitems_on_screen-1)))[1]

        # Normal click
        elif clicked(clickpos, (0,0), config.resolution):

            # Get index of item clicked
            click_index = (clickpos[1] + self.list_offset)//size["listitem_height"]
            if click_index > len(self.pc["list"]["viewcontent"])-1:
                click_index = -1

            # Check return value: True if staying in list view with new content
            next_view = self.pc["list"]["click"](click_index, mousebutton)
            if next_view == "listview":
                self.switch_view("listview")
            else:
                self.switch_view("main")

        # Return value: allow repeat
        return False

    def scroll_listview(self, start, direction, end=False):
        x, y = direction
        allow_smoothscroll = False
        self.scroll_start = start

        # Prevent negative offset for short lists that fit on the screen
        if len(self.pc["list"]["viewcontent"]) > self.listitems_on_screen:
            max_offset = size["listitem_height"]*(len(self.pc["list"]["viewcontent"])-self.listitems_on_screen)
        else:
            max_offset = 0

        # Scrollbar: fast scroll
        if clicked(start, pos("scrollbar_click"), size["scrollbar_click"]):
            ratio = float(-32.0 + start[1] + y)*1.20
            ratio = ratio/float(config.resolution[1])
            self.list_offset = int(ratio*size["listitem_height"]*(len(self.pc["list"]["viewcontent"])))
            self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, max_offset))[1]

        # Normal scroll
        else:
            # Limit X Scroll to the length of the menuitem buttons
            if x > 0:
                x = (x//self.list_scroll_threshold)*self.list_scroll_threshold
                x = limit_offset((x,0),(0, 0, len(self.pc["list"]["buttons"])*self.list_scroll_threshold,0))[0]

            self.draw_offset = limit_offset((x,y),(-config.resolution[0], -10*config.resolution[1],
                                                    config.resolution[0],  10*config.resolution[1]))
            # Allow smooth scrolling
            if abs(y) > 0:
                allow_smoothscroll = True

        # Scroll ended
        if end:
            self.scroll_start = -1,-1
            self.list_offset = self.list_offset - self.draw_offset[1]
            self.list_offset = limit_offset((0,self.list_offset),(0, 0, 0, max_offset))[1]
            self.draw_offset = (0,0)

            # Horizontal scroll right does something for the item
            if x >= self.list_scroll_threshold:
                button = 2 + x//self.list_scroll_threshold
                self.click_listview(button, start)

            # Horizontal scroll left exits
            elif x <= -self.list_scroll_threshold:
                self.click_listview(-1, start)

        return allow_smoothscroll

    def update_ack(self, item):
        self.status["update"][item] = False
        
    def updated(self, item="all"):
        if item == "all":
            return True in self.status["update"].values()
        else:
            return self.status["update"][item]

    def force_update (self,item="all"):
        if item == "all":
            self.status["update"] = dict.fromkeys(self.status["update"], True)
        else:
            self.status["update"][item] = True
