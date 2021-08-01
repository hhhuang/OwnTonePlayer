# -*- coding: utf-8 -*-

import datetime
from hashlib import sha1
import json
import os
import sys

import pathlib

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtCore import *
 
from owntone_client import * 

from libs.background_task import run_async, run_async_mutex, run_loop, remove_threads
from kb.kb_prediction import get_recommendation_list

owntone_client = None

def get_artwork(album, update=False):
    if not album.artwork_url:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artworks', "blank.jpg")
    #   Using the last two folders as the key because it is migratable.
    d1, d2 = os.path.split(os.path.dirname(album.tracks[0]['path']))
    _, d1 = os.path.split(d1)
    #   All files in the same folder (album) share the same artwork.
    artwork_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artworks', d1, d2 + ".jpg")
    #   Extract the embedded artwork from the file on the fly.
    
    if os.path.isfile(artwork_path):
        if pathlib.Path(artwork_path).stat().st_size > 0:
            return artwork_path
        elif not update:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artworks', "blank.jpg")
            
    if owntone_client.download_artwork(album.artwork_url, artwork_path):
        return artwork_path

    if not os.path.isdir(os.path.dirname(artwork_path)):
        os.mkdir(os.path.dirname(artwork_path))
    pathlib.Path(artwork_path).touch()
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artworks', "blank.jpg")
  

def createRecommendationGrid():
   # Create table
    table = QTableWidget()
    table.setShowGrid(False)
    table.horizontalHeader().hide()
    table.verticalHeader().hide()
    #table.setRowCount((len(items) + 2) // 3)
    table.setColumnCount(8)
    table.setColumnWidth(0, 150)
    table.setColumnWidth(1, 150)
    table.setColumnWidth(2, 15)
    table.setColumnWidth(3, 150)
    table.setColumnWidth(4, 150)
    table.setColumnWidth(5, 15)
    table.setColumnWidth(6, 150)
    table.setColumnWidth(7, 150)
    return table

def createTrackTable():
    # Create table
    table = QTableWidget()
    table.setRowCount(0)
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(["Disc", "Track", "Title", "Artist", "Length"])
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.Stretch)
    header.setSectionResizeMode(3, QHeaderView.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    return table

    
def updateTrackTable(table, tracks, key_field):
    table.setRowCount(len(tracks))
    for i in range(len(tracks)):
        track = tracks[i]
        title = TableItem(track['title'])
        title.setData(Qt.UserRole, track[key_field])
        table.setItem(i, 0, TableItem(str(track['disc_number'])))
        table.setItem(i, 1, TableItem(str(track['track_number'])))
        table.setItem(i, 2, title)
        table.setItem(i, 3, TableItem(track['artist']))
        table.setItem(i, 4, TableItem(str(datetime.timedelta(seconds=int(track['length_ms'] // 1000)))))
        table.move(0,0)


class AlbumPopup(QDialog):
    def __init__(self, main, album):
        super().__init__(main)
        self.name = "Album"
        self.main = main
        self.album = album

        self.setWindowTitle(album.title + " - " + album.artist)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setWindowFlag(Qt.WindowSystemMenuHint, True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.createAlbumSection())        
        self.layout.addWidget(self.createTrackSection())        
        self.layout.addWidget(self.createControlSection())        
        self.setLayout(self.layout) 
        self.show()
        
    def createAlbumSection(self):
        artwork_file = get_artwork(self.album)
        img = QPixmap(artwork_file)
        artwork = QLabel(self)
        artwork.setPixmap(img.scaled(300, 300, Qt.KeepAspectRatio))
        
        metadata = [('Title', self.album.title), ('Artist', self.album.artist)]
        for k in ['composer', 'genre', 'year', 'bitrate', 'samplerate', 'channels']:
            if k in ['bitrate', 'samplerate']:
                lower = min([int(track.get(k, 0)) for track in self.album.tracks])
                upper = max([int(track.get(k, 0)) for track in self.album.tracks])
                if lower == upper:
                    metadata.append((k, str(lower)))
                else:
                    metadata.append((k, "%d-%d" % (lower, upper)))
            else:
                metadata.append((k, ", ".join(set([str(track.get(k, "")) for track in self.album.tracks]))))
        metadata.append(('Last modified', self.album.last_modified))
        metadata.append(('Path', str(os.path.dirname(self.album.tracks[0]['path']))))
                
        grid = QGridLayout()
        #   Get artwork and show

        grid.addWidget(artwork, 0, 0, len(metadata), 1)

        for row, (k, v) in enumerate(metadata):
            grid.addWidget(QLabel(k + ": ", self), row, 1)
            label = QLabel(v, self)
            label.setWordWrap(True)
            grid.addWidget(label, row, 2, 1, 8)
   
        section = QGroupBox()
        section.setLayout(grid)
        return section
        
    def createTrackSection(self):
        self.table = createTrackTable()
        updateTrackTable(self.table, self.album.tracks, 'uri')
        #        self.albumTable.doubleClicked.connect(self.item_on_double_click)
        self.table.clicked.connect(self.item_on_click)           
        return self.table
               
        
    def createControlSection(self):
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.cancel_on_click)
                
        self.play_button = QPushButton('Play', self)
        self.play_button.clicked.connect(self.play_on_click)

        section = QGroupBox()
        section.setLayout(QHBoxLayout())
        section.layout().addWidget(self.cancel_button)
        section.layout().addWidget(self.play_button)
        return section

    @pyqtSlot()
    def item_mouse_over(self):
        """        """
        pass
        
    @pyqtSlot()
    def item_on_click(self):
        for currentTableItem in self.table.selectedItems():
            print(currentTableItem.row(), currentTableItem.column(), currentTableItem.text())
            self.table.setRangeSelected(QTableWidgetSelectionRange(currentTableItem.row(), 0, currentTableItem.row(), self.table.columnCount() - 1), True)
    
    @pyqtSlot()
    def cancel_on_click(self):
        self.close()
        
    @pyqtSlot()
    def play_on_click(self):
        print("Play on click!")
        print(self.album.title)         
        self.main.player.pause()
        self.main.playqueue.clear()       
        if not self.table.selectedItems():  # Add the entire album.
            self.main.playqueue.add_album(self.album, True)
        else:                               # Add the selected tracks.
            tracks = [item.data(Qt.UserRole) for item in self.table.selectedItems() if item.column() == 2]
            self.main.playqueue.set_tracks(tracks, playback=True)
        self.main.updatePlaylist()
        self.close()
        
        
class ConfigPopup(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.name = "Configuration"
        self.main = main

        self.setWindowTitle("Configuration")
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowSystemMenuHint, False)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        self.host_label = QLabel("Host: ", self)
        self.host_input = QLineEdit(main.config['host'], self)
        self.host_input.setMaximumWidth(300)

        self.port_label = QLabel("Port: ", self)
        self.port_input = QLineEdit(str(main.config['port']), self)
        self.port_input.setMaximumWidth(300)
        
        self.volume_label = QLabel("Default Volume: ", self)
        self.volume_input = QLineEdit(str(main.config['volume']), self)
        self.volume_input.setMaximumWidth(300)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.cancel_on_click)
                
        self.ok_button = QPushButton('Ok', self)
        self.ok_button.clicked.connect(self.ok_on_click)
        
        self.layout = QGridLayout()
        self.layout.addWidget(self.host_label, 0, 0)
        self.layout.addWidget(self.host_input, 0, 1)
        self.layout.addWidget(self.port_label, 1, 0)
        self.layout.addWidget(self.port_input, 1, 1)
        self.layout.addWidget(self.volume_label, 2, 0)
        self.layout.addWidget(self.volume_input, 2, 1)
        self.layout.addWidget(QLabel("Outputs", self), 3, 0)

        row = 4
        self.output_checkboxes = {}
        for output in main.outputs.status():
            o = QCheckBox(output['name'], self)
            o.setChecked(output['selected'])
            o.stateChanged.connect(self.toggle_output)
            self.output_checkboxes[output['id']] = o
            self.layout.addWidget(o, row, 0, 1, 2)
            row += 1
        self.layout.addWidget(self.cancel_button, row, 0)
        self.layout.addWidget(self.ok_button, row, 1)
        
        self.setLayout(self.layout) 
        self.show()
    
    @pyqtSlot()
    def toggle_output(self):
        selected = []
        for output_id, o in self.output_checkboxes.items():
            if o.isChecked():
                selected.append(output_id)
        print(selected)
        self.main.outputs.set_outputs(selected)
        
    @pyqtSlot()
    def cancel_on_click(self):
        self.close()
        
    @pyqtSlot()
    def ok_on_click(self):
        self.main.config['host'] = self.host_input.text().strip()
        self.main.config['port'] = int(self.port_input.text().strip())
        self.main.config['volume'] = int(self.volume_input.text().strip())
        self.main.save_config()
        self.main.initClient()
        self.close()


class TableItem(QTableWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlags(self.flags() ^ Qt.ItemIsEditable)  #  Read only
    
    def enterEvent(self, QEvent):
        pass
        
    def leaveEnter(self, QEvent):
        pass
        
        
class App(QWidget): 
    def __init__(self):
        self.albums = []
        super().__init__()
        self.title = 'OwnTone Player for Audiophiles'
        self.left = 256
        self.top = 128
        self.width = 1024
        self.height = 768
        self.log_file = "log.txt"
        
        self.initUI()
        self.load_config()
        try:
            self.initClient()
            run_async(self.initData, self.initPlayer)
        except:
            self.loading_widget.setText("Fail to load the music library.\nCheck the setting of your OwnTone server in the Options menu and restart this player.")
            #self.popup_configuration()
        
    def __del__(self):
        pass
        
    def load_config(self):
        try:
            with open("config.json") as fin:
                self.config = json.load(fin)            
        except:
            self.config = {'host': 'localhost', 'port': 3689, 'volume': 100}
            
    def save_config(self):
        with open("config.json", "w") as fout:
            json.dump(self.config, fout)
        
    def initClient(self):
        global owntone_client
        owntone_client = connect_server(self.config['host'], self.config['port'])
        self.client = owntone_client
    
    def initPlayer(self):
        self.server_mutex = QMutex()
        self.music_lib = Library(self.client, update=False)
        self.playqueue = PlayQueue(self.client)
        self.player = Player(self.client)
        self.player.setvol(self.config['volume'])
        self.outputs = Outputs(self.client)
        self.slider_moving = False
        
    def initData(self, results=None):
        collection = self.music_lib.list_latest_albums()
        self.updateAlbumTable(collection)
        self.updatePlaylist()
        self.updateRecommendation(collection)
        
        self.update_status()
        self.update_local_info()        
        
        self.local_updator = QTimer(self)
        self.local_updator.timeout.connect(self.update_local_info)
        self.local_updator.start(1000)
        
        self.server_updator = QTimer(self)
        self.server_updator.timeout.connect(self.update_status)
        self.server_updator.start(10000)
        
    def setPlaying(self, playing):
        self.playing = playing
        if playing:
            self.play_button.setChecked(True)
            self.play_button.setText('Pause')
        else:
            self.play_button.setChecked(False)
            self.play_button.setText('Play')
                  
    def createMenuBar(self):
        self.config_action = QAction("Configure", self)
        self.config_action.triggered.connect(self.popup_configuration)

        self.rebuild_action = QAction("Rebuild Library", self)
        self.rebuild_action.triggered.connect(self.rebuild_library)
        
        self.artwork_action = QAction("Update Artworks", self)
        self.artwork_action.triggered.connect(self.build_all_artworks)
                
        self.menuBar = QMenuBar()
        self.option_menu = self.menuBar.addMenu('Options')
        self.option_menu.addAction(self.config_action)
        self.option_menu.addAction(self.rebuild_action)
        self.option_menu.addAction(self.artwork_action)
        
        self.list_view_action = QAction("List", checkable=True, checked=False)
        
        self.small_grid_view_action = QAction("Small Grid", checkable=True, checked=False)
        self.medium_grid_view_action = QAction("Medium View", checkable=True, checked=False)
        self.large_grid_view_action = QAction("Large Grid", checkable=True, checked=True)
        self.extra_large_grid_view_action = QAction("Extra Large Grid", checkable=True, checked=False)
                        
        self.list_view_action.toggled.connect(self.change_album_view)
        self.small_grid_view_action.toggled.connect(self.change_album_view)
        self.medium_grid_view_action.toggled.connect(self.change_album_view)
        self.large_grid_view_action.toggled.connect(self.change_album_view)
        self.extra_large_grid_view_action.toggled.connect(self.change_album_view)
       
        self.view_group = QActionGroup(self)
        self.view_group.setExclusive(True)
        self.view_group.addAction(self.list_view_action)
        self.view_group.addAction(self.small_grid_view_action)
        self.view_group.addAction(self.medium_grid_view_action)
        self.view_group.addAction(self.large_grid_view_action)
        self.view_group.addAction(self.extra_large_grid_view_action)
       
        self.view_menu = self.menuBar.addMenu('View')
        self.view_menu.addAction(self.list_view_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.small_grid_view_action)
        self.view_menu.addAction(self.medium_grid_view_action)
        self.view_menu.addAction(self.large_grid_view_action)
        self.view_menu.addAction(self.extra_large_grid_view_action)
                
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'misc', 'icon.png')))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.statusBar = QStatusBar(self)
        self.createMenuBar()
        self.createControlPanel()  
        self.createAlbumTable()
        self.createAlbumGrid()
        self.playlist = createTrackTable()
        self.playlist.clicked.connect(self.playlist_on_click)
        self.current_track_info = QGroupBox()
        self.current_track_info.setLayout(QGridLayout())
        self.renderLayout()                
        
    def event(self, event):
        if event.type() in [QEvent.NonClientAreaMouseButtonRelease, QEvent.WindowStateChange]:
            print("Event deteted.")
            if not self.list_view_action.isChecked():
                ideal_num_columns, _, _ = self.computeGridSize()
                current_num_columns = self.albumGrid.columnCount() - 1  #   There is addionional column as the left maring.
                if ideal_num_columns != current_num_columns:
                    self.updateAlbumTable(None)
        return super().event(event)
        
    def renderLayout(self):
        self.layout = QVBoxLayout()
        self.layout.setMenuBar(self.menuBar)
        self.layout.addWidget(self.controlPanel)
        
        #self.album_tab = QFrame()
        #self.album_tab.setLayout(QVBoxLayout())
        #self.album_tab.layout().addWidget(self.albumTable)
        #self.album_tab.layout().addWidget(self.statusBar)
        
        #self.playlist_tab = QFrame()
        #self.pla2ylist_tab.setLayout(QVBoxLayout())
        #self.playlist_tab.layout().addWidget(self.playlist)
        
        self.stacked_tab = QStackedWidget()
        self.loading_widget = QLineEdit("Loading...", self)
        self.loading_widget.setAlignment(Qt.AlignCenter)
        self.stacked_tab.addWidget(self.loading_widget)
        self.stacked_tab.addWidget(self.albumTable)        
        self.stacked_tab.addWidget(self.albumGrid)
                        
        self.recommendation = createRecommendationGrid()
                
        self.tabs = QTabWidget()
        self.tabs.addTab(self.stacked_tab, "Albums")
        self.tabs.addTab(self.playlist, "Playlist")
        self.tabs.addTab(self.current_track_info, "Playing")        
        #self.tabs.addTab(self.recommendation, "Recommendation")
        
        self.layout.addWidget(self.tabs) 
        self.layout.addWidget(self.statusBar)
        self.setLayout(self.layout) 
        self.show()
                    
    def updateStatusBar(self, albums):
        num_discs = 0
        num_tracks = 0
        total_seconds = 0
        for album in albums:
            album_discs = set()
            for track in album.tracks:
                album_discs.add(track['disc_number'])
                total_seconds += int(track['length_ms'] // 1000)
            num_tracks += len(album.tracks)
            num_discs += len(album_discs)
        status = "Number of albums: %d, Number of disks: %d, Number of tracks: %d, Total time: %s" % (len(albums), num_discs, num_tracks, str(datetime.timedelta(seconds=total_seconds)))
        self.statusBar.showMessage(status)
        
    def createControlPanel(self):
        self.play_button = QPushButton('Play', self)
        self.play_button.setCheckable(True)
        self.play_button.clicked.connect(self.play_on_click)
               
        self.infobox = QLineEdit("", self)
        self.infobox.setReadOnly(True)
        
        self.time_info = QLabel("", self)
        
        self.seek_slider = QSlider(Qt.Horizontal, self)
        self.seek_slider.setMaximumWidth(120)
        self.seek_slider.sliderPressed.connect(self.slider_pressed)
        self.seek_slider.sliderReleased.connect(self.slider_released)
        
        self.search_box = QLineEdit("", self)
        self.search_box.setMaximumWidth(120)
        self.search_box.returnPressed.connect(self.search_box_entered)
        self.search_box.textChanged.connect(self.search_button_reset)
        self.search_button = QPushButton('Search', self)
        self.search_button.clicked.connect(self.search_on_click)
                
        self.volume_slider = QSlider(Qt.Horizontal, self)
        self.volume_slider.setMaximumWidth(32)
        #self.volume_slider.setMaximumHeight(24)
        self.volume_slider.setMinimum(0)            
        self.volume_slider.setMaximum(100) 
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.sliderPressed.connect(self.volume_pressed)
        self.volume_slider.sliderReleased.connect(self.volume_released)
        
        layout = QHBoxLayout()
        layout.addWidget(self.play_button)
        layout.addWidget(self.infobox)
        layout.addWidget(self.seek_slider)
        layout.addWidget(self.time_info)
        layout.addWidget(self.search_box)
        layout.addWidget(self.search_button)
        layout.addWidget(self.volume_slider)
        
        self.controlPanel = QGroupBox()    
        self.controlPanel.setMaximumHeight(60)
        self.controlPanel.setLayout(layout)

    @pyqtSlot()
    def playlist_on_click(self):
        items = [item['uri'] for item in self.playqueue.list()]
        self.playqueue.set_tracks(items, position=self.playlist.currentRow(), playback=True)
        self.update_status()

    @pyqtSlot()       
    def update_local_info(self):
        if self.playing:
            self.playing_time += 1
        self.time_info.setText("%d/%d" % (self.playing_time, self.track_time))
        if not self.slider_moving:
            self.seek_slider.setValue(self.playing_time)
                
    @pyqtSlot()
    def update_status(self):
        track = self.playqueue.get_current_song()
        """{'id': 3358, 'position': 42, 'track_id': 11633, 'title': "Così fan tutte, K. 588: Act 2: 'Abbi Di Me Pietà, Dammi Consiglio' - Aria Guglielmo 'Donne Mie'", 'artist': 'Concerto Köln/Werner Güra/René Jacobs/Marcel Boone/Wolfgang Amadeus Mozart/Concerto Köln', 'artist_sort': 'Concerto Köln/Werner Güra/René Jacobs/Marcel Boone/Wolfgang Amadeus Mozart/Concerto Köln', 'album': 'Mozart: Così fan tutte', 'album_sort': 'Mozart: Così fan tutte', 'album_id': '5036546791084034588', 'album_artist': 'Concerto Köln, René Jacobs and Kölner Kammerchor, Kölner Kammerchor, Concerto Köln, René Jacobs', 'album_artist_sort': 'Concerto Köln, René Jacobs and Kölner Kammerchor, Kölner Kammerchor, Concerto Köln, René Jacobs', 'album_artist_id': '4809176959249518758', 'composer': 'Wolfgang Amadeus Mozart', 'genre': 'Classical', 'year': 0, 'track_number': 43, 'disc_number': 0, 'length_ms': 213066, 'media_kind': 'music', 'data_kind': 'file', 'path': "/disk2/share/Music/Music/Concerto Köln, René Jacobs and Kölner Ka/Mozart_ Così fan tutte/43 Così fan tutte, K. 588_ Act 2_ 'A.m4a", 'uri': 'library:track:11633', 'artwork_url': './artwork/item/11633', 'type': 'm4a', 'bitrate': 643, 'samplerate': 44100, 'channels': 2}"""

        status = self.player.status()
        """{'state': 'play', 'repeat': 'off', 'consume': False, 'shuffle': False, 'volume': 100, 'item_id': 3358, 'item_length_ms': 213066, 'item_progress_ms': 370, 'artwork_url': './artwork/nowplaying'}"""

        output_str = ",".join([o['name'] for o in self.outputs.status() if o['selected']])
        
        if track and status and 'album' in track and 'item_length_ms' in status:
            self.infobox.setText("%s: %d-%d %s %s" % (track['album'], int(track['disc_number']), int(track['track_number']), track['title'], track['artist']))
            self.playing_time = status['item_progress_ms'] // 1000
            self.track_time = status['item_length_ms'] // 1000

            if status['state'] == 'play':
                self.setPlaying(True)
            else:
                self.setPlaying(False)
            
            #   Highlight the playing track in the playlist.
            self.playlist.setRangeSelected(QTableWidgetSelectionRange(0, 0, self.playlist.rowCount() - 1, self.playlist.columnCount() - 1), False)
            self.playlist.setRangeSelected(QTableWidgetSelectionRange(int(track['position']), 0, int(track['position']), self.playlist.columnCount() - 1), True)            
            self.seek_slider.setMinimum(0)
            self.seek_slider.setMaximum(self.track_time)
            self.volume_slider.setValue(int(status['volume']))
            self.volume_slider.setMinimum(0)            
            self.volume_slider.setMaximum(100) 
            if output_str:
                output_str = " (%s)" % output_str
            self.volume_slider.setToolTip("Volume: %d%s" % (status['volume'], output_str))
            
            album = self.music_lib.get_album_by_tmp_id(track['album_id'])
            self.updateCurrentTrackInfo(album, track)
        else:
            self.infobox.setText("")
            self.time_info.setText("")
            self.setPlaying(False)
            self.seek_slider.setValue(0)
            self.playing_time = 0
            self.track_time = 0
            
    @pyqtSlot()
    def slider_pressed(self):
        self.slider_moving = True
        
    @pyqtSlot()
    def slider_released(self):    
        self.player.seek(self.seek_slider.value())
        self.slider_moving = False
        self.update_local_info()
            
    @pyqtSlot()
    def volume_pressed(self):
        self.volume_moving = True
        
    @pyqtSlot()
    def volume_released(self):
        self.player.setvol(self.volume_slider.value())
        self.volume_moving = False
        self.update_status()
            
    @pyqtSlot()
    def play_on_click(self):
        try:
            if self.playing:
                self.setPlaying(False)
                self.player.pause()
            else:
                self.setPlaying(True)
                self.player.play()
        except:
            self.handle_error()
            
    def handle_error(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Fail to connect the player")
        msg.setInformativeText("There are something wrong about the connection with the player. Click OK to reload the player.")
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(self.initClient)
        retval = msg.exec_()
        print("value of pressed message box button:", retval)

    @pyqtSlot()
    def stop_on_click(self):
        self.player.pause()

    @pyqtSlot()
    def search_box_entered(self):
        self.search()
        
    @pyqtSlot()
    def search_on_click(self):
        self.search()
       
    @pyqtSlot()
    def popup_configuration(self):
        exPopup = ConfigPopup(self)
        #exPopup.setGeometry(100, 200, 100, 200)
        exPopup.setMinimumSize(100, 200)
        exPopup.show()

    @pyqtSlot()
    def rebuild_library(self):
        def post_process():
            self.updateAlbumTable(self.music_lib.list_latest_albums(10000000))  
            
        def call_rebuild():
            self.music_lib = Library(self.client, update=True)
            
        self.stacked_tab.setCurrentIndex(0)
        run_async_mutex(self.server_mutex, post_process, call_rebuild)

    @pyqtSlot()
    def build_all_artworks(self):
        def post_process():
            self.updateAlbumTable(self.music_lib.list_latest_albums(10000000))  
        
        def call_rebuild():
            i = 0
            albums = self.music_lib.list_latest_albums(10000000)
            for album in albums:
                get_artwork(album, update=True)
                i += 1
                if i % 100 == 0:
                    print("%d / %d have been processed." % (i, len(albums)))
                    
        self.stacked_tab.setCurrentIndex(0)
        run_async(post_process, call_rebuild)
        
    @pyqtSlot()
    def change_album_view(self):
        self.updateAlbumTable()
        
    @pyqtSlot()
    def search_button_reset(self):
        if self.search_button.text() == 'Clean':
            self.search_button.setText('Search')

    def search(self):
        if self.search_button.text() == 'Clean':
            query = ""
            self.search_button.setText('Search')
            self.search_box.setText('')
        else:
            query = self.search_box.text().strip()
        print(query)
        if not query:
            albums = self.music_lib.list_latest_albums(10000000)
        else:
            albums = self.music_lib.search(query.split())
            self.search_button.setText('Clean')
        print("Number of albums found: %d" % len(albums))
        self.updateAlbumTable(albums)

    def updateAlbumTable(self, albums=None):
        if albums is None:
            albums = self.albums
        else:
            self.albums = albums
        if self.list_view_action.isChecked():
            self.fillAlbumTable(albums)
            self.stacked_tab.setCurrentIndex(1)        
        else:
            self.fillAlbumGrid(albums)
            self.stacked_tab.setCurrentIndex(2)            
        self.updateStatusBar(albums)
        self.layout.update()
        self.update()
        
    def fillAlbumTable(self, albums):
        self.albumTable.clearContents()
        self.albumTable.setRowCount(len(albums))
        self.albumTable.setVerticalHeaderLabels(["⏵"]*len(albums))
        for i in range(len(albums)):
            title = TableItem(albums[i].title)
            title.setData(Qt.UserRole, albums[i].album_id)
            self.albumTable.setItem(i, 0, title)
            self.albumTable.setItem(i, 1, TableItem(albums[i].artist))
            self.albumTable.setItem(i, 2, TableItem(albums[i].last_modified[:10]))
        self.albumTable.move(0,0)
        self.sorted_order = Qt.DescendingOrder
        self.sorted_column = 2
        self.albumTable.sortItems(self.sorted_column, self.sorted_order)
        
    def updatePlaylist(self):
        print("Updating playlist")
        updateTrackTable(self.playlist, self.playqueue.list(), 'uri')
        print("Updating Status")
        self.update_status()
#        self.albumTable.doubleClicked.connect(self.item_on_double_click)
#        self.playlist.clicked.connect(self.item_on_click)           
        
    def updateRecommendation(self, collection):
        table = self.recommendation
        items = get_recommendation_list(collection, 0)["album"]
     
        table.setRowCount((len(items) + 2) // 3)
        for idx, data in enumerate(items):
            img = QPixmap(data['cover_path'])
            cover_item = TableItem("")
            cover_item.setTextAlignment(Qt.AlignCenter)
            cover_item.setData(Qt.DecorationRole, img.scaled(140, 140, Qt.KeepAspectRatio))

            info = TableItem("%s\nBy %s\n%s, %s\nAMG Rating: %s" % (
                data['title'], data['artist'], data['label'], data['year'], data['rating']))
            info.setData(Qt.UserRole, data["link"])
            row = idx // 3
            col = (idx % 3) * 3
            table.setItem(row, col, cover_item)
            table.setItem(row, col + 1, info) 
            if col == 0:
                table.setRowHeight(row, 150)
                table.setItem(row, 2, TableItem(""))
                table.setItem(row, 5, TableItem(""))
        table.move(0, 0)
        
    def createAlbumTable(self):
        # Create table
        self.albumTable = QTableWidget()
        self.albumTable.setRowCount(0)
        self.albumTable.setColumnCount(3)
        self.albumTable.setHorizontalHeaderLabels(["Title", "Aritst", "Last Modified"])
        header = self.albumTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
#        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
#        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.sectionClicked.connect(self.header_on_click)      
        
        row = self.albumTable.verticalHeader()
        row.sectionClicked.connect(self.row_on_click)
        
        # table selection change
        self.albumTable.doubleClicked.connect(self.item_on_double_click)
        self.albumTable.clicked.connect(self.item_on_click)
        
    def getThumbnailSize(self):        
        if self.extra_large_grid_view_action.isChecked():
            return 256
        elif self.large_grid_view_action.isChecked():
            return 216
        elif self.small_grid_view_action.isChecked():
            return 150
        else: 
            return 180

    def createAlbumGrid(self):
       # Create table
        self.albumGrid = QTableWidget()
        self.albumGrid.setStyleSheet("QTableWidget::item:selected{ background-color: transparent; color: black} QTableWidget {selection-background-color: transparent; selection-color: black}")
        self.albumGrid.setShowGrid(False)
        self.albumGrid.horizontalHeader().hide()
        self.albumGrid.verticalHeader().hide()
        self.albumGrid.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # table selection change
        self.albumGrid.doubleClicked.connect(self.grid_item_on_double_click)
        self.albumGrid.clicked.connect(self.grid_item_on_click)
        self.artwork_pixmap_cache = {}
        
    def getGridItem(self, album):
        if album.album_id not in self.artwork_pixmap_cache:
            self.artwork_pixmap_cache[album.album_id] = QPixmap(get_artwork(album))
        img = self.artwork_pixmap_cache[album.album_id]
        
        thumbnail = TableItem("")
        thumbnail.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        thumbnail.setData(Qt.DecorationRole, img.scaled(self.getThumbnailSize(), self.getThumbnailSize(), Qt.KeepAspectRatio))
        thumbnail.setData(Qt.UserRole, album.album_id)
        thumbnail.setToolTip("%s\n%s" % (album.title, album.artist))
        
        info = TableItem("%s\n%s" % (album.title, album.artist))
        info.setTextAlignment(Qt.AlignCenter | Qt.AlignTop);
        info.setData(Qt.UserRole, album.album_id)
        
        return thumbnail, info
        
    def computeGridSize(self) -> (int, int, int):
        grid_width = int(self.getThumbnailSize() * 1.05)
        grid_height = int(self.getThumbnailSize() * 1.05)
        tab_width = self.stacked_tab.size().width() - 20 # 20 pixels for the Y scrolling bar.
        num_columns = int(tab_width // (grid_width))
        return num_columns, grid_width, grid_height
    
    def fillAlbumGrid(self, albums):       
        num_columns, grid_width, grid_height = self.computeGridSize()
        spacing = max(0, int(((self.stacked_tab.size().width() - 20) - (num_columns * grid_width)) // 2 - 5))
        
        table = self.albumGrid
        table.clearContents()        
        table.setColumnCount(num_columns + 1)
        table.setRowCount(2 * int((len(albums) + num_columns - 1) // num_columns))
        
        #self.albumGrid.setColumnWidth(0, left_margin)
        for i in range(0, table.columnCount()):
            if i == 0:
                table.setColumnWidth(i, spacing)
            else:
                table.setColumnWidth(i, grid_width)
        
        for idx, album in enumerate(albums):
            thumbnail, info = self.getGridItem(album)
            row = int((idx // num_columns) * 2)
            col = int(idx % num_columns)
            table.setItem(row, col + 1, thumbnail)
            table.setItem(row + 1, col + 1, info) 
            if col == 0:
                spacer = TableItem("")
                spacer.setData(Qt.UserRole, "Spacer")
                table.setItem(row, 0, spacer)
                spacer = TableItem("")
                spacer.setData(Qt.UserRole, "Spacer")
                table.setItem(row + 1, 0, spacer)
                table.setRowHeight(row, grid_height)
                table.setRowHeight(row + 1, 50)
        table.move(0, 0)
                      
    def updateCurrentTrackInfo(self, album, track):
        grid = self.current_track_info.layout()
        #   Do nothing for the same track
        if grid.objectName() == track['uri']:
            return
        print("Update Current Track info")
        artwork_file = get_artwork(album)
        img = QPixmap(artwork_file)
        artwork = QLabel(self)
        artwork.setPixmap(img.scaled(600, 600, Qt.KeepAspectRatio))
        metadata = [('Album title', album.title), ('Album artist', album.artist)]
        for k in ['title', 'artist', 'composer', 'genre', 'year', 'track_number', 'disc_number', 'length_ms', 'bitrate', 'samplerate', 'channels', 'time_added', 'path']:
            if k == 'length_ms':
                metadata.append(('Length', str(datetime.timedelta(seconds=int(track.get(k, 0) / 1000)))))
            else:
                metadata.append((k[0].upper() + k[1:].replace("_", " "), str(track.get(k, ""))))
        while True:
            item = grid.takeAt(0)
            if not item:
                break
            w = item.widget()
            w.deleteLater()
            del item
            
        #   Get artwork and show
        grid.addWidget(artwork, 0, 0, len(metadata), 1)
        row = 0
        for k, v in metadata:
            grid.addWidget(QLabel(k + ": ", self), row, 1)
            entry = QLabel(v, self)
            entry.setWordWrap(True)
            grid.addWidget(entry, row, 2, 1, 8) 
            row += 1
        grid.setObjectName(track['uri'])
        #self.layout.update()
        #self.update()    
           
    @pyqtSlot()
    def grid_item_on_click(self):
        row = self.albumGrid.currentRow()
        col = self.albumGrid.currentColumn()
        album_id = self.albumGrid.item(row, col).data(Qt.UserRole)
        if album_id == "Spacer":
            return
        self.popup_album(album_id)
    
    @pyqtSlot()
    def grid_item_on_double_click(self):
        row = self.albumGrid.currentRow()
        col = self.albumGrid.currentColumn()
        album_id = self.albumGrid.item(row, col).data(Qt.UserRole)
        if album_id == "Spacer":
            return
        print("Play on click!")
        self.main.playqueue.add_album(album_id, playback=True)
        self.main.updatePlaylist()

    @pyqtSlot()
    def item_on_click(self):
        row = self.albumTable.currentRow()
        self.albumTable.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, self.albumTable.columnCount() - 1), True)          

    @pyqtSlot()
    def item_on_double_click(self):
        row = self.albumTable.currentRow()
        album_id = self.albumTable.item(row, 0).data(Qt.UserRole)
        self.popup_album(album_id)
    
    def popup_album(self, album_id):
        album = self.music_lib.get_album(album_id)
        exPopup = AlbumPopup(self, album)
        exPopup.setGeometry(100, 100, 1024, 768)
        exPopup.show()  
    
    @pyqtSlot()
    def row_on_click(self):
        self.play_selected()
        
    @pyqtSlot()
    def header_on_click(self):
        column = self.albumTable.selectedItems()[0].column()
        if column == self.sorted_column:
            if self.sorted_order == Qt.AscendingOrder:
                self.sorted_order = Qt.DescendingOrder
            else:
                self.sorted_order = Qt.AscendingOrder
        else:
            if column == 2:
                self.sorted_order = Qt.DescendingOrder
            else:
                self.sorted_order = Qt.AscendingOrder
            
        self.albumTable.sortItems(column, self.sorted_order)
        self.sorted_column = column
            
    def play_selected(self):
        if not self.albumTable.selectedItems():
            try:
                self.player.play()
            except:
                print("Fail to call play()")
                self.handle_error()
            return
        albums = [item.data(Qt.UserRole) for item in self.albumTable.selectedItems() if item.column() == 0]
        self.player.pause()
        self.playqueue.clear()
        self.playqueue.add_albums(albums, True)
        self.updatePlaylist()

        with open(self.log_file, "a", encoding="utf8") as fout:
            for album in albums:
                tracks = self.music_lib.get_album(album).tracks
                for track in tracks:
                    fout.write("%s\t%s\n" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), track['path']))
                    
    def closeEvent(self, event):
        print("Closing window")
        remove_threads()
        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
    
