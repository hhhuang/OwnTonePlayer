# OwnTone Player for Audiophiles

This is an audiophile-oriented remote controller for the [OwnTone](https://github.com/owntone/owntone-server) music server (previously forked-daapd), migrated from a previous project for the [MPD](https://www.musicpd.org) protocol. 
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

The cost of this player (actually a remote controller) is its resource hungry nature. 
For a collection of about 3,000 disks and 40,000 tracks, the process of this player can consume more than 2G of memory in a Windows 10 environment. 

## Key Features
* Friendly with a large number of albums. The player has been tested with a collection more than 3,000 CDs.
* This player is album-oriented. All the tracks in the OwnTone server are reorganized into albums. Compared with individual tracks, album is a much more structural and meaningful unit for serious music lovers' critical listening. 
* Many audio grade music servers and renderers are built on low-power devices such as NAS and Raspberry Pi. To reduce the loads of these devices, all the loading are taken by the controller side (i.e. this player). This design philosophy results a slim, mimimal, somewhat slow player, but both server/renderer sides benefit from stability, lower jitter, and better sound quailty. 

## Environment Requirement
* Python 3
* QT 5
* Operating system: Windows/Mac/Linux and so on. The code has been verified on Windows 10 and Mac OS Mojave.
* A collection of audio files that is manipulated by an OwnTone server. [More information of the setup of the OwnTone server](https://github.com/owntone/owntone-server). The OwnTone server has to enable websocket for receiving push notifications. 
* An ideal setting is comprised of a standalone music server running the OwnTone service, a standalone music renderer like a Hi-Fi DAC/Stream Player that supports Apple AirPlay or [Shairport Sync](https://github.com/mikebrady/shairport-sync), and this player installed on another powerful desktop/laptop in the same LAN. 

## Setup

### Install related packages

```pip install -r requirements.txt```

### Assign the MPD music server and restart the player

Configure the OwnTone server in the file ```config.json``` as follows for your OwnTone server at ```192.168.0.1'''.

```{"host": "192.168.0.1", "port": 3689, "volume": 100}```

## Usage

### Start the player

```python player_gui.py```
  
### Rebuild the library for your music collection

In the first time, the player takes some time depending on the size of your music collection. 
For a collection of 3,000 CDs on a remote SSD, the procedure will perform in 10 minutes. 

<img src="misc/loading.png?raw=true" width=640 />

### Play an album
<img src="misc/player_gui.png?raw=true" width=640 />

### Browse the albums in the grid view
Four sizes of the grid views are available. 
The player spends a number of seconds when it launchs the grid view or list view. 

<img src="misc/player_gui_grid_view.png?raw=true" width=640 />

### Config the OwnTone server and select output devices
<img src="misc/setting.png?raw=true" width=640 />

## Issues to Note
### Added Dates
The only time information returned by the OwnTone server is `time_added`, which is the time the file being imported into the database. 
`time_added` is less useful if you rebuild your database several times. 
The other time information stored in the OwnTone database, `time_modified`, is more useful since it is the last time the file being modifieid. 
The current OwnTone API does not return `time_modified` so you can hack the OwnTone database in the following way.

1. Open the database

    ```
    sqlite3 songs3.db
    ```

2. Replace the `time_added` with `time_modified` for each file

    ```sql
    UPDATE files SET time_added = time_modified;
    ```

For the files originally maintained by an official iTunes server, the [script](update_creation_time.py) extracts the their creation date from the iTunes metadata, and updates the time_added fields in the OwnTone database.

### Artwork

The OwnTone server provides the embedded artwork of albums. 
For an album that does not contain the embedded artwork, the great tool [get_cover_art](https://github.com/regosen/get_cover_art/tree/master/get_cover_art) can be used for automatically searching the artwork from iTunes and embedding the artwork into the file. 
The tool can perform on the folder of the entire music collection for embedding all the files. 
