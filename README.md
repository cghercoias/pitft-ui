PiTFT-UI is a fork of PMB-PiTFT (Pi MusicBox PiTFT), a small Python script that uses mopidy's mpd-api to show controlling ui on Raspberry Pi's screen.
Forked from https://github.com/Arzk/pitft-playerui

![Screenshot](https://dl.dropboxusercontent.com/s/c2x5mcrbz4xqm0j/pitft-playerui.gif)

Features:
===========
Shows following details of currently playing track in MPD and Spotify:
- Cover art from local folder.jpg etc file, Spotify or Last.FM
- Artist, Album and Track title
- Track time total and elapsed (Only in MPD)

Shows and lets user control:
- Playback status
- Repeat and random
- Volume
- Playlists and library (MPD only)

Main screen gestures:
- Coverart click: play/pause
- Vertical scrolling: switch player (down), player menus(up)
- Horizontal flip: next/previous
- Volume and progressbar: scroll or click

List view:
- Item click: Select
- Long click: Alternative action
- Vertical scrolling
- Horizontal flip: exit (left), additional commands (right)

Things you need:
=================
- Raspberry pi (I am using model 3)
- Adafruit PiTFT+ 3.5" with Resistive Touchscreen ( https://www.adafruit.com/product/2441 )
- Internet connection for Pi
- Raspbian running on the Pi (developing on Stretch, but Jessie was also ok)
- [Optional] MPD configured
- [Optional] Spotify-connect-web configured
- [Optional] Last.fm API key for cover art fetching
- [Optional] Helvetica Neue Bold-font. You can use normal Helvetica Bold as well or some other font.

Known issues:
==============
- CDDB tag fetching does not work well together with MPD playback. Planning to switch the CD player to mplayer
- Inaccurate touchscreen calibration/detection using Raspbian Jessie/Stretch with sdl2, need to force downgrade sdl to 1.2 version (script provided in repo scripts/forcesdl_1.2, modify to your liking)
- Restart command occasionally gives unnecessary SIGTERMs to the newly started instance

Installing:
===========
Current installation guide is tested and working with: Resistive PiTFT+ 3.5", PiFi DAC+ and Raspberry Pi 3 running Raspbian Stretch.

Install Raspbian and MPD and Configure PiTFT+ using the guide by Adafruit: https://learn.adafruit.com/adafruit-pitft-3-dot-5-touch-screen-for-raspberry-pi/ 
Detailed install and calibration recommended

For the player switching to work when using a separate DAC with no hardware mixer, set up dmix in alsa

For PiFi DAC+ open /boot/config.txt and add the line:

<code>dtoverlay=i2s-mmap</code>

Open /etc/asound.conf and add the following:

<pre>
pcm.!default {
 type plug
 slave.pcm "pifi"
}

pcm.pifi {
    type softvol
    slave {
        pcm "dacci_dmix"
    }
    control  {
        name "PCM"
        card sndrpihifiberry
    }
}

pcm.dacci_dmix {
    type dmix
    ipc_key 1024
    ipc_perm 0666
    slave {
      pcm dacci
      period_time 0
      period_size 2048
      buffer_size 32768
      rate 44100
   }
   bindings {
      0 0
      1 1
   }
}

pcm.dacci {
 type hw
 card sndrpihifiberry
}
ctl.dacci {
 type hw
 card sndrpihifiberry
}
</pre>

This should set MPD and Spotify to use the same softvol volume slider. To set the balance between players, use the replaygain preamp settings in mpd.conf.

Install dependencies:
<pre>apt-get update
apt-get install python-pygame python-lirc python-cddb
pip install python-mpd2
apt-get install evtest tslib libts-bin
</pre>

For Spotify support install spotify-connect-web:
https://github.com/Fornoth/spotify-connect-web

Download PiTFT-playerui files from github. To be sure to start in the home directory do
<code>cd</code>

Clone the git repository:
<code>git clone https://github.com/Arzk/pitft-playerui.git</code>

Copy config.py.in to config.py

For lirc support, copy pitft-playerui.lircrc.in to pitft-playerui.lircrc and modify your buttons

From config.py you need to change the font if you are using something else than Helvetica Neue Bold and check that path is correct.
You can download for example Open Sans "OpenSans-Bold.ttf" from www.fontsquirrel.com/fonts/open-sans. Transfer ttf file to /home/pi/pitft-playerui/ folder.

Set the other settings in config.py file:
- Resolution defaults to 480x320. Set to 320x240 if using 2.8" PiTFT (not implemented yet)
- For local cover art set the path of the mpd library
- Set the LastFM api key and login information for remote cover art fetching
- For Spotify set the path and port of Spotify-connect-web
- To disable MPD support and use only spotify, clear the mpd_host and mpd_port

This is a daemon and it has three commands: start, restart and stop.
Use the following command to start ui:

<code>sudo python /home/pi/pitft-playerui/ui.py start</code>

To run the script as a service, copy the systemd service file to /etc/systemd/system:

<code>sudo cp scripts/pitft-playerui.service /etc/systemd/system/</code>

Note that using the framebuffer requires root access. The script can also be run in X window, for example via X forwarding in PuTTY, without sudo (but give your user write permission to the logs).

Some specific things:
=========
- The active player view is decided between MPD and Spotify so that:
	- On start the playing player is active. Pause one if both are playing
	- If Spotify is playing and MPD starts playing, pause Spotify and switch to MPD
	- Vice versa if Spotify starts playing

TODO:
=========
- 320x240 support
- CD player with mplayer
- Support for OpenHome Mediaplayer (http://petemanchester.github.io/MediaPlayer/)
- Sleep timer and other settings in a separate menu
- Got other ideas? Post an issue and tell me about it

Author notes:
=============
There might be some bugs left, so let me hear about them. Feel free to give any improvement ideas. This is my first python project, so a lot of things could surely be done more efficiently.

Thanks:
===========
<pre>ISO-B
For the pmb-pitft
https://github.com/ISO-B/pmb-pitft</pre>

<pre>Fornoth
For the Spotify Connect Web
https://github.com/Fornoth/spotify-connect-web</pre>

<pre>Ben Gertzfield
For the CDDB module
http://cddb-py.sourceforge.net/</pre>

<pre>Notro and other people on project FBTFT
For making drivers for screen
https://github.com/notro/fbtft/wiki</pre>

<pre>project pylast @ github
For their Last.FM Python library
https://github.com/pylast/pylast</pre>

<pre>project python-mpd2 @ github
For their MPD-client Python library
https://github.com/Mic92/python-mpd2</pre>

<pre>Matt Gentile @ Icon Deposit
For his awesome Black UI Kit that these icons are based on
http://www.icondeposit.com/design:108</pre>

<pre>Biga
Petite Icons
http://www.designfreebies.com/2011/10/20/petite-icons/</pre>
