# Owntone Player for Audiophiles

This is an audiophile music player for [the OwnTone server (previously forked-daapd)](https://github.com/owntone/owntone-server), migrated from my previous [project](https://github.com/hhhuang/mpd_player) for the [MPD](https://www.musicpd.org) protocol. 
This player is designed for the purpose of audio playback, aiming to deal with two core issues in network audio playback.

Firstly, the traditional clients are lightweight, leeaving heavy load for the music servers to support functions such as browsing, search, and streaming artworks.
These jobs can cause a significant latency to the sensitive audio-grade music servers. 
In order to improve the sound quality, the loads of the music server and the renderer are minimized. 
The philosophy is to handle most of loads in this player, which is nearly isolated from the real-time playback loop.
In other words, the functions including browsing and search are locally performed by this player. 
All the metadata of albums, as well as artworks, are locally cached in the client. 
In this way, the music server can focus on streaming the music data to the renderer with almost zero load for other tasks. 

Secondly, many players are not designed for true music lovers who have a large collection of albums. 
It is not uncommon that the user-inferace got annoyingly slow when more than 1,000 albums were imported.
We design this player with this consideration in mind, providing an elegant and friendly user-interface for efficiently handling a large collection of albums. 

## Key Features
* Friendly with a large number of albums. The player has been tested with a collection more than 3,000 CDs.
* This player is album-oriented. All the tracks in the OwnTone server are reorganized into albums. Compared with individual tracks, album is a much more structural and meaningful unit for serious music lovers' critical listening. 
* Many audio grade music servers and renderers are built on low-power devices such as NAS and Raspberry Pi. To reduce the loads of these devices, all the loading are taken by the controller side (i.e. this player). This design philosophy results a slim, mimimal, somewhat slow player, but both server/renderer sides benefit from stability, lower jitter, and better sound quailty. 

## Environment Requirement
* Python3
* Operating system: Windows/Mac/Linux and so on. The code has been verified on Windows 10 and Mac OS Mojave.
* A collection of audio files that is manipulated by an OwnTone server. [More information of the setup of the OwnTone server](https://github.com/owntone/owntone-server).
* An ideal setting is comprised of a standalone music server running the OwnTone service, a standalone music renderer like a Hi-Fi DAC/Stream Player that supports Apple AirPlay or [Shairport Sync](https://github.com/mikebrady/shairport-sync), and this player installed on another powerful desktop/laptop in the same LAN. 

## Setup

### Install related packages

```pip install -r requirements.txt```

### Assign the MPD music server and restart the player

Configure the OwnTone server in the file ```config.json``` as follows.

```{"host": "192.168.0.1", "port": 3689, "volume": 100}```

## Usage

### Start the player

```python player_gui.py```
  
### Rebuild the library for your music collection

In the first time, the player takes some time depending on the size of your music collection. 
For a collection of 3,000 CDs on a remote SSD, the procedure will perform in 10 minutes. 

<img src="https://github.com/hhhuang/OwnTonePlayer/blob/master/misc/loading.png?raw=true" width=640 />

### Play an album
<img src="https://github.com/hhhuang/OwnTonePlayer/blob/master/misc/player_gui.png?raw=true" width=640 />

### Browse the albums in the grid view
<img src="https://github.com/hhhuang/OwnTonePlayer/blob/master/misc/player_gui_grid_view.png?raw=true" width=640 />

### Config the OwnTone server and select output devices
<img src="https://github.com/hhhuang/OwnTonePlayer/blob/master/misc/setting.png?raw=true" width=640 />


