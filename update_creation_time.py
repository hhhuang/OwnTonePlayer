from urllib.parse import unquote
from html import unescape
import time
import datetime
import sys
import re
import os
import sqlite3

def make_timestamp(time_str):
    return int(time.mktime(datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ").timetuple()))

def read_track(fin):
    while True:
        line = fin.readline()
        if len(line) == 0:
            return None
        if line.strip() == '<key>Playlists</key>':
            return None
        if re.match('^<key>[^<]+<\/key>$', line.strip()):
            break
    else:
        return None
    fin.readline()
    data = {}
    while True:
        line = fin.readline()
        if len(line) == 0:
            raise ValueError("EOF before the closing tag")
        line = line.strip()
        if not line:
            continue
        if line == '</dict>':
            break
        if line[0] == '<' and line[-1] != '>':
            while True:
                line += "\n" + fin.readline().strip()
                if line[-1] == '>':
                    break
        result = re.findall('^<key>([^<]+)<\/key>(<[^>]+>([^<]+)|(<([^\/]+)\/>))', line.strip())
        if not result:
            print(line.strip())
            continue
        if result[0][2]:
            data[result[0][0]] = unescape(result[0][2])
        else:
            data[result[0][0]] = unescape(result[0][4])
    if 'Location' not in data:
        print("Data no location")
        print(data)
        return False
    data['Location'] = unquote(data['Location']).replace('/Music//Music/', '/Music/Music/')
    for k in ["Date Modified", "Date Added"]:
        data[k] = make_timestamp(data[k])
    return data

def read_tracks(filename):
    with open(filename, encoding="utf8") as fin:
        while True:
            line = fin.readline()
            if len(line) == 0:
                break
            if line.strip() == '<key>Tracks</key>':
                break
        while True:
            track = read_track(fin)
            if track is None:
                break
            if track == False:
                continue
            yield track

def update(conn, data):
    if not data['Location'].startswith("file://localhost//192.168.11.235/share/Music/Music/"):
        return False
    path = "/disk2" + data['Location'][len("file://localhost//192.168.11.235"):]

    """sqlite> select path, time_added, time_modified from files limit 1;
       /disk2/share/Music/Music/Yes/90125/03 It Can Happen.m4a|1558865402|1558865402"""
    cur = conn.cursor()
    cur.execute("UPDATE files SET time_added = MIN(?, time_added, time_modified) WHERE path = ?", (
                min(data['Date Modified'], data['Date Added']), path))
    if cur.rowcount == 1:
        return True

    cur.execute("UPDATE files SET time_added = MIN(?, time_added, time_modified) WHERE path LIKE ?", (
                min(data['Date Modified'], data['Date Added']), path))
    if cur.rowcount == 1:
        return True

    print(track['Location'] + " is not found in the db.")
    return False

if __name__ == "__main__":
    filename = '/disk2/share/Music/iTunes/iTunes Library (Damaged) 3.xml'
    conn = sqlite3.connect("songs3.db")
    cnt = 0
    fails = 0
    for track in read_tracks(filename):
        if not update(conn, track):
            fails += 1
        else:
            cnt += 1
            if cnt % 1000 == 0:
                print(cnt)
                conn.commit()
    print("Total modified: %d" % cnt)
    print("Total failed: %d" % fails)
    conn.commit()
    conn.close()

