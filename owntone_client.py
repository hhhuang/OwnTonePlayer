# -*- coding: utf-8 -*-

import json
import jsonpickle
import os.path
import os
import requests
import shutil

from libs.collation import latin2ascii
#from kb import database as knowledge_base
#album_kb = knowledge_base.load_albums()


class OwnToneAPI(object):
    def __init__(self, host='localhost', port=3689):
        self.host = host
        self.port = port
        
    def make_url(self, target, action):
        command = target
        if action:
            command += '/' + action
        return "http://" + self.host + ":" + str(self.port) + "/api/" + command
        
    def call(self, method, target, action='', data = None, **parameters):
        if data is None:
            data = {}
        else:
            data = json.dumps(data)
            
        url = self.make_url(target, action)
        if method == 'get':
            response = requests.get(url=url, data=data, params=parameters)
        elif method == 'put':
            response = requests.put(url=url, data=data, params=parameters)
        elif method == 'post':
            response = requests.post(url=url, data=data, params=parameters)
        elif method == 'delete':
            response = requests.delete(url=url, data=data, params=parameters)

        if response.status_code == 204:
            return True
        if 200 <= response.status_code < 300:

            return response.json()
        else:
            print(response.status_code)
            print("Wrong request: ")
            print(url)
            print(parameters)
            return False
            
    def download_artwork(self, artwork_url, target_filename):
        url = "http://" + self.host + ":" + str(self.port) + "/" + artwork_url[2:]
        print(url)
        r = requests.get(url, stream=True)
        print(r.status_code)
        if r.status_code == 200:
            if not os.path.isdir(os.path.dirname(target_filename)):
                os.mkdir(os.path.dirname(target_filename))
            with open(target_filename, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)   
                return True
        print("The image is not found")
        return False
        
def connect_server(host='localhost', port=3689):
    conn = OwnToneAPI(host, port)
    print(conn)
    return conn    

class Album(object):
    def __init__(self, raw_album):
        self.album_id = raw_album['uri']
        self.tracks = raw_album['tracks']
        self.title = raw_album['name']
        self.last_modified = raw_album['time_added']
        self.artist = raw_album['artist']
        self.artwork_url = raw_album['artwork_url']
        self.keywords = ""
        self.complete()
        
    def search_kb(self):
        return []
        global album_kb
        for a in album_kb:
            pass
            
    def get_metadata(self):
        return []       
        
    def match(self, keywords):
        for keyword in keywords:
            if latin2ascii(keyword.lower()) not in self.keywords:
                return False
        return True
                
    def complete(self):
        self.get_metadata()
        self.gen_keywords()
        self.sort_tracks()
    
    def sort_tracks(self):
        self.tracks.sort(key=lambda x: (x['disc_number'], x['track_number']))
    
    def gen_keywords(self):
        keywords = set([self.title.lower(), self.artist.lower()])
        for track in self.tracks:
            keywords.add(latin2ascii(track['title'].lower()))
            keywords.add(latin2ascii(track['artist'].lower()))
            keywords.add(latin2ascii(track['album_artist'].lower()))
            keywords.add(latin2ascii(track.get('composer', '').lower()))
            keywords.add(latin2ascii(track.get('genre', '').lower()))
        self.keywords = " ".join(keywords)        
        
    def __cmp__(self, other):
        return cmp(self.last_modified, other.last_modified)
               
    
class Library(object):
    def __init__(self, client, update=False):
        self.client = client
        self.cache_path = "library.json"
        self.album_path = "albums.json"
        if update:
            self.update()
        self.build()
    
    def update(self):
        data = self.client.call('get', 'library', 'albums')
        print(data['total'])
        data = data['items']
        num_tracks = 0
        for i in range(len(data)):
            data[i]['tracks'] = self.client.call('get', 'library', "albums/%s/tracks" % str(data[i]['id']))['items']
            num_tracks += len(data[i]['tracks'])
        print("Number of tracks: %d" % num_tracks)
        with open(self.cache_path, "w") as fout:
            json.dump(data, fout)
        
    def build(self):
        cached_albums = []
        try:
            with open(self.cache_path) as fin:
                cached_albums = json.load(fin)     
                print("Load %d albums from cached file %s" % (len(cached_albums), self.cache_path))
        except:
            print("Cached file for albums is not found.")
        print("building albums from json")
        albums = self.build_albums(cached_albums)
        with open(self.album_path, "w") as fout:
            json.dump(jsonpickle.encode(albums), fout)
        
    def build_albums(self, data):
        self.albums = {}
        self.tmp_lookup = {}
        num_tracks = 0
        self.latest_albums = []
        for entry in data:
            album = Album(entry)
            self.albums[album.album_id] = album
            self.tmp_lookup[entry['id']] = album
            num_tracks += len(album.tracks)
            self.latest_albums.append((album.album_id, album.last_modified))    
        print("Number of albums: %d, Number of tracks: %d" % (len(self.albums), num_tracks))
        self.latest_albums.sort(key=lambda x: x[1], reverse=True)
        print("All albums have been built")
        
    def get_album(self, album_id):
        return self.albums[album_id]
        
    def get_album_by_tmp_id(self, album_tmp_id):
        return self.tmp_lookup[album_tmp_id]
    
    def list_latest_albums(self, size=None):
        if size is None:
            size = len(self.latest_albums)
        albums = []
        for album_id, _ in self.latest_albums[:size]:
            albums.append(self.get_album(album_id))
        return albums
    
    def search(self, keywords):
        albums = []
        keywords = list(map(str.lower, keywords))
        for album in self.albums.values():
            if album.match(keywords):
                albums.append(album)
        return albums
        
#    def find(self):
#        albums = self.client.find({"any": ""}, "Album", 0, 10)
#        print(albums)
#        print(len(albums))
        
    
class PlayQueue(object):
    def __init__(self, client):
        self.client = client
        
    def add_album(self, album, playback=False):
        if isinstance(album, str):
            uris = album
        elif isinstance(album, Album):
            uris = album.album_id
        else:
            raise ValueError("The album should be either an uri or an Album instance.")
            
        if playback:
            return self.client.call('post', 'queue', 'items/add', uris=uris, playback="start")
        else:
            return self.client.call('post', 'queue', 'items/add', uris=uris)       
        
    def add_albums(self, albums, playback=False):
        if (not isinstance(albums, list)) or len(albums) < 1:
            raise ValueError("Albums is a non-empty list.")
        if isinstance(albums[0], str):
            uris = ",".join(albums)
        elif isinstance(albums[0], Album):
            uris = ",".join([album.album_id for album in albums])
        else:
            raise ValueError("The album should be either an uri or an Album instance.")

        if playback:
            return self.client.call('post', 'queue', 'items/add', uris=uris, playback="start")
        else:
            return self.client.call('post', 'queue', 'items/add', uris=uris)
         
    def set_tracks(self, tracks, position=0, playback=False):
        if playback:
            return self.client.call('post', 'queue', 'items/add', uris=",".join(tracks), clear=True, playback_from_position=position, playback="start")
        else:
            return self.client.call('post', 'queue', 'items/add', uris=",".join(tracks), clear=True, playback_from_position=position)
                                
    def add_track(self, album, track):
        return self.client.call('post', 'queue', 'items/add', uris=[album.tracks[track - 1]['uri']])
                    
    def clear(self):
        return self.client.call('put', 'queue', 'clear')
    
    def list(self):
        items = self.client.call('get', 'queue')['items']
        return items
        
    def get_current_song(self):
        item_id = self.client.call('get', 'player').get('item_id', None)
        if item_id:
            for item in self.list():
                if item['id'] == item_id:
                    return item
        return None
        
        
class Player(object):
    def __init__(self, client):
        self.client = client
        
    def play(self):
        return self.client.call('put', 'player', 'play')
       
    def stop(self):
        return self.client.call('put', 'player', 'stop')
        
    def pause(self):
        return self.client.call('put', 'player', 'pause')
        
    def toggle(self):
        return self.client.call('put', 'player', 'toggle')

    def next(self):
        return self.client.call('put', 'player', 'next')
    
    def previous(self):
        return self.client.call('put', 'player', 'previous')
        
    def shuffle(self, state: bool):
        return self.client.call('put', 'player', 'shuffle', state=state)
    
    def consume(self, state: bool):
        return self.client.call('put', 'player', 'consume', state=state)
   
    def repeat(self, state: str):
        if state not in ["off", "all", "single"]:
            raise ValueError("State must be in either off, all, or single")
        return self.client.call('put', 'player', 'consume', state=state)   
   
    def status(self):
        return self.client.call('get', 'player')
        
#    def idle(self, *args, **kwargs):
#        return self.client.idle(*args, **kwargs)
                       
#    def noidle(self):
#        return self.client.noidle()
        
    def seek(self, time: int):
        return self.client.call('put', 'player', 'seek', position_ms=time*1000)
        
    def skip_to(self, item_id):
        items = self.client.call('get', 'queue')['items']
        tgt = None
        for i in range(len(items)):
            if items[i]['id'] == item_id:
                tgt = i
                break
        if not tgt:
            raise ValueError("Target item is not found: %r" % item_id)
               
        src = 0
        current = self.status()
        if current['item_id']:
            for i in range(len(items)):
                if items[i]['id'] == current['item_id']:
                    src = i
                    break
        
        print("From %d to %d" % (src, tgt))
        if src < tgt:
            for _ in range(tgt - src):
                self.next()
                
        elif src > tgt:
            for _ in range(src - tgt):
                self.previuos()
        else:
            self.next()
            self.previous()
            #   Restart the current track        
        
    def setvol(self, vol: int):
        return self.client.call('put', 'player', 'volume', volume=vol)


class Outputs(object):
    def __init__(self, client):
        self.client = client         
    
    def status(self):
        return self.client.call('get', 'outputs')['outputs']
        
    def toggle(self, output_id):
        return self.client.call('put', 'outputs', "%s/toggle" % str(output_id))
        
    def set_outputs(self, output_ids):
        return self.client.call('put', 'outputs', "set", data={"outputs": output_ids})
    
def show_list(albums):
    print("Number of albums: %d" % len(albums))
    for album in albums:
        print("%s: %s %s" % (album.album_id, album.title, album.artist))
        
def show_album(album):
    print("%s: %s %s" % (album.album_id, album.title, album.artist))
    for track in album.tracks:
        print("%2d:%3d - %s %s" % (track['disc'], track['track'], track['title'], track['artist']))

if __name__ == "__main__":
    client = connect_server('192.168.11.235', 3689)
    music_lib = Library(client, update=False)
    pq = PlayQueue(client)
    player = Player(client)

    pause = False
    while True:
        cmd = input()
        rows = cmd.split()
        cmd = rows[0]
        if cmd == 'q':
            break
        elif cmd == 'p':
            if len(rows) >= 2:
                pq.clear()
                if len(rows) == 2:
                    album = music_lib.get_album(rows[1])
                    pq.add_album(album, True)
                    show_album(album)
                elif len(rows) == 3:
                    album = music_lib.get_album(rows[1])
                    track = int(rows[2])
                    pq.add_track(album, track, True)
                    show_album(album)
            print(player.status())
        elif cmd == 's':
            player.pause()
        elif cmd == 'latest':
            size = int(rows[1]) if len(rows) == 2 else 20
            show_list(music_lib.list_latest_albums(size))
        elif cmd == 'search':
            show_list(music_lib.search(rows[1:]))
        elif cmd == 'v':
            show_album(music_lib.get_album(int(rows[1])))
        elif cmd == 'update':
            music_lib = Library(client, update=True)
        elif cmd == 'status':
            print(player.status())
            for track in pq.list():
                print(track)
            print(pq.get_current_song())    
        #elif cmd == 'idle':
        #    print(player.idle())
        elif cmd == 'volume':
            player.setvol((int(rows[1])))
        elif cmd == 'find':
            music_lib.find()
        else:
            print("Unknown command: %s" % cmd)
