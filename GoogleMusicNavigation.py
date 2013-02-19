import os
import sys
import urllib
import CommonFunctions as common

class GoogleMusicNavigation():
    def __init__(self):
        self.main = sys.modules["__main__"]
        self.xbmc = self.main.xbmc
        self.xbmcgui = self.main.xbmcgui
        self.xbmcplugin = self.main.xbmcplugin
        self.xbmcvfs = self.main.xbmcvfs

        self.settings = self.main.settings
        self.language = self.settings.getLocalizedString

        self.api  = self.main.api
        self.song = self.main.song

        self.main_menu = (
            {'title':self.language(30208), 'params':{'path':"search"}},
            {'title':self.language(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.language(30202), 'params':{'path':"playlists", 'playlist_type':"user"}},
            {'title':self.language(30204), 'params':{'path':"playlists", 'playlist_type':"auto"}},
            {'title':self.language(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.language(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.language(30207), 'params':{'path':"filter", 'criteria':"genre"}}
        )

    def listMenu(self, params={}):
        get = params.get
        path = get("path", "root")

        listItems = []

        if path == "root":
            ''' Show the plugin root menu. '''
            for menu_item in self.main_menu:
                params = menu_item['params']
                cm = []
                if 'playlist_id' in params:
                    cm = self.getPlayAllContextMenuItems(params['playlist_id'])
                elif 'playlist_type' in params:
                    cm = self.getPlaylistsContextMenuItems(params['playlist_type'])
                listItems.append(self.addFolderListItem(menu_item['title'], params, cm))
        elif path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
        elif path == "playlists":
            playlist_type = get('playlist_type')
            if playlist_type in ('auto', 'instant', 'user'):
                listItems = self.getPlaylists(playlist_type)
            else:
                self.main.log("Invalid playlist type: " + playlist_type)
        elif path == "filter":
            criteria  = get('criteria')
            listItems = self.getCriteria(criteria)
        elif path in ["genre","artist","album"]:
            filter_criteria = get('name')
            listItems = self.listFilterSongs(path,filter_criteria)
        elif path == "search":
            listItems = self.getSearch()
        else:
            self.main.log("Invalid path: " + get("path"))

        self.xbmcplugin.addDirectoryItems(int(sys.argv[1]), listItems)
        self.xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=True)

    def executeAction(self, params={}):
        get = params.get
        if (get("action") == "play_all"):
            self.playAll(params)
        elif (get("action") == "play_song"):
            self.song.play(get("song_id"))
        elif (get("action") == "update_playlist"):
            self.api.getPlaylistSongs(params["playlist_id"], True)
        elif (get("action") == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (get("action") == "clear_cache"):
            self.clearCache()
        elif (get("action") == "clear_cookie"):
            self.clearCookie()
        else:
            self.main.log("Invalid action: " + get("action"))

    def addFolderListItem(self, name, params={}, contextMenu=[], album_art_url=""):
        li = self.xbmcgui.ListItem(label=name, iconImage=album_art_url, thumbnailImage=album_art_url)
        li.setProperty("Folder", "true")

        url = sys.argv[0] + '?' + urllib.urlencode(params)

        if len(contextMenu) > 0:
            li.addContextMenuItems(contextMenu, replaceItems=True)

        #return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        #self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li)#, isFolder=True)
        return url, li, "true"

    def addSongItem(self, song):
        song_id = song[0].encode('utf-8')

        li = self.song.createItem(song)

        url = '%s?action=play_song&song_id=%s' % (sys.argv[0], song_id)
        #return self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li)
        #self.xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li)
        return url,li

    def listPlaylistSongs(self, playlist_id):
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        return self.addSongsFromLibrary(songs)

    def addSongsFromLibrary(self, library):
        listItems = []
        for song in library:
            listItems.append(self.addSongItem(song))
        return listItems

    def getPlaylists(self, playlist_type):
        self.main.log("Getting playlists of type: " + playlist_type)
        playlists = self.api.getPlaylistsByType(playlist_type)
        return self.addPlaylistsItems(playlists)

    def listFilterSongs(self, filter_type, filter_criteria):
        if filter_criteria:
            filter_criteria = urllib.unquote_plus(filter_criteria)
        songs = self.api.getFilterSongs(filter_type, filter_criteria)
        return self.addSongsFromLibrary(songs)

    def getCriteria(self, criteria):
        listItems = []
        genres = self.api.getCriteria(criteria)
        for genre in genres:
	    if genre[1]:
		    art = 'http:' + genre[1]
	    else:
		    art = self.main.__icon__

            listItems.append(self.addFolderListItem(genre[0], {'path':criteria, 'name':genre[0].encode('utf8')}, album_art_url=art))
        return listItems

    def addPlaylistsItems(self, playlists):
        listItems = []
        for playlist_id, playlist_name, playlist_type, fetched in playlists:
            cm = self.getPlayAllContextMenuItems(playlist_id)
            listItems.append(self.addFolderListItem(playlist_name, {'path':"playlist", 'playlist_id':playlist_id}, cm))
        return listItems

    def playAll(self, params={}):
        get = params.get

        playlist_id = get('playlist_id')
        self.main.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)

        player = self.xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = self.xbmc.PlayList(self.xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        song_url = "%s?action=play_song&song_id=%s&playlist_id=" + playlist_id
        for song in songs:
            song_id = song[0].encode('utf-8')

            li = self.song.createItem(song)
            playlist.add(song_url % (sys.argv[0], song_id), li)

        if (get("shuffle")):
            playlist.shuffle()

        self.xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def getPlayAllContextMenuItems(self, playlist):
        cm = []
        cm.append((self.language(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (sys.argv[0], playlist)))
        cm.append((self.language(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (sys.argv[0], playlist)))
        cm.append((self.language(30303), "XBMC.RunPlugin(%s?action=update_playlist&playlist_id=%s)" % (sys.argv[0], playlist)))
        return cm

    def getPlaylistsContextMenuItems(self, playlist_type):
        cm = []
        cm.append((self.language(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (sys.argv[0], playlist_type)))
        return cm

    def clearCache(self):
        sqlite_db = os.path.join(self.xbmc.translatePath("special://database"), self.settings.getSetting('sqlite_db'))
        if self.xbmcvfs.exists(sqlite_db):
            self.xbmcvfs.delete(sqlite_db)

        self.settings.setSetting("fetched_all_songs", "")
        self.settings.setSetting('firstrun', "")

        self.clearCookie()

    def clearCookie(self):
        cookie_file = os.path.join(self.settings.getAddonInfo('path'), self.settings.getSetting('cookie_file'))
        if self.xbmcvfs.exists(cookie_file):
            self.xbmcvfs.delete(cookie_file)

        self.settings.setSetting('logged_in', "")

    def getSearch(self):
        query = common.getUserInput(self.language(30208), '')
        if not query:
           return False
        results = self.api.getSearch(query)
        return self.addSongsFromLibrary(results)

