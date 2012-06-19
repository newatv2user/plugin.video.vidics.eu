import urllib, urllib2, re, sys, cookielib, os
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from xbmcgui import ListItem
import CommonFunctions
import StorageServer
import urlresolver
import string

# plugin constants
### get addon info
Addon = xbmcaddon.Addon()
AddonId = Addon.getAddonInfo('id')
PluginHandle = int(sys.argv[1])

rootDir = Addon.getAddonInfo('path')
if rootDir[-1] == ';':
    rootDir = rootDir[0:-1]
rootDir = xbmc.translatePath(rootDir)
#settingsDir = Addon.getAddonInfo('profile')
#settingsDir = xbmc.translatePath(settingsDir)
#cacheDir = os.path.join(settingsDir, 'cache')

# For parsedom
common = CommonFunctions
common.dbg = False
common.dbglevel = 3

# initialise cache object to speed up plugin operation
cache = StorageServer.StorageServer(AddonId, 2)

programs_thumb = os.path.join(rootDir, 'resources', 'media', 'programs.png')
topics_thumb = os.path.join(rootDir, 'resources', 'media', 'topics.png')
search_thumb = os.path.join(rootDir, 'resources', 'media', 'search.png')
next_thumb = os.path.join(rootDir, 'resources', 'media', 'next.png')
movies_thumb = os.path.join(rootDir, 'resources', 'media', 'movies.jpg')
tv_thumb = os.path.join(rootDir, 'resources', 'media', 'television.jpg')
shows_thumb = os.path.join(rootDir, 'resources', 'media', 'shows.png')
video_thumb = os.path.join(rootDir, 'resources', 'media', 'movies.png')
az_thumb = os.path.join(rootDir, 'resources', 'media', 'atoz.jpg')
added_thumb = os.path.join(rootDir, 'resources', 'media', 'Date_Added.jpg')
popular_thumb = os.path.join(rootDir, 'resources', 'media', 'most_popular.jpg')

########################################################
## URLs
########################################################
BASE_URL = 'http://www.vidics.eu'

## Category
Categories = {"Films": "Movies",
              "TV-Shows": "TvShows",
              "Short": "Short"}

########################################################
## Modes
########################################################
M_DO_NOTHING = 0
M_BROWSE = 10
M_SOURCES = 20
M_BROWSE_SEASON = 30
M_TV = 50
M_PLAY = 40
M_SEARCH = 60
M_GENRES = 80
M_YEARS = 90
M_LETTERS = 100
M_SORT = 110

##################
## Class for items
##################
class MediaItem:
    def __init__(self):
        self.ListItem = ListItem()
        self.Image = ''
        self.Url = ''
        self.Isfolder = False
        self.Mode = ''
        
## Get URL
def getURL(url):
    print 'getURL :: url = ' + url
    cj = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2;)')]
    response = opener.open(url)
    html = response.read()
    ret = {}
    ret['html'] = html 
    return ret

# Save page locally
'''def save_web_page(url, filename):
    f = open(os.path.join(cacheDir, filename), 'w')
    data = getURL(url)
    f.write(data['html'])
    f.close()
    return data['html']
    
# Read from locally save page
def load_local_page(filename):
    f = open(os.path.join(cacheDir, filename), 'r')
    data = f.read()
    f.close()
    return data'''

def BuildUrl(urlDict):
    Url = BASE_URL + '/Category-' + urlDict['Category']
    Url += '/Genre-' + urlDict['Genre']
    if urlDict['Years']:
        Url += '/' + urlDict['Years']
    Url += '/Letter-' + urlDict['Letter']
    Url += '/' + urlDict['Sort']
    Url += '/' + urlDict['Page']
    if urlDict['Search']:
        Url += '/Search-' + urlDict['Search']
    Url += '.htm'
    return Url

def GetUrlDict(Url=None, DfltCategory=None):
    UrlDict = {}
    if not Url:
        if not DfltCategory:
            return None
        UrlDict['Category'] = DfltCategory
        UrlDict['Genre'] = 'Any'
        UrlDict['Years'] = None
        UrlDict['Letter'] = 'Any'
        UrlDict['Sort'] = 'LatestFirst'
        UrlDict['Page'] = '1'
        UrlDict['Search'] = None
    else:
        Category = Url.split('Category-')[1]
        Category = Category.split('/')[0]
        Genre = Url.split('Genre-')[1]
        Genre = Genre.split('/')[0]
        GenreSp = Url.split('Genre-')[1]
        GenLetSp = GenreSp.split('Letter-')[0]
        Years = GenLetSp.split('/')[1]
        if Years == '':
            Years = None
        LetterO = Url.split('Letter-')[1]
        Letter = LetterO.split('/')[0]
        Sort = LetterO.split('/')[1]
        Page = LetterO.split('/')[2]
        if "htm" in Page:
            Page = Page.split('.htm')[0]
        Search = Url.split('Search-')
        if len(Search) > 1:
            Search = Search[1].split('.htm')[0]
        else:
            Search = None
        UrlDict['Category'] = Category
        UrlDict['Genre'] = Genre
        UrlDict['Years'] = Years
        UrlDict['Letter'] = Letter
        UrlDict['Sort'] = Sort
        UrlDict['Page'] = Page
        UrlDict['Search'] = Search
    return UrlDict

def cleanHtml(dirty):
    # Remove HTML codes
    clean = re.sub('&quot;', '\"', dirty)
    clean = re.sub('&#039;', '\'', clean)
    clean = re.sub('&#215;', 'x', clean)
    clean = re.sub('&#038;', '&', clean)
    clean = re.sub('&#8216;', '\'', clean)
    clean = re.sub('&#8217;', '\'', clean)
    clean = re.sub('&#8211;', '-', clean)
    clean = re.sub('&#8220;', '\"', clean)
    clean = re.sub('&#8221;', '\"', clean)
    clean = re.sub('&#8212;', '-', clean)
    clean = re.sub('&amp;', '&', clean)
    clean = re.sub("`", '', clean)
    clean = re.sub('<em>', '[I]', clean)
    clean = re.sub('</em>', '[/I]', clean)
    clean = re.sub('<strong>', '', clean)
    clean = re.sub('</strong>', '', clean)
    clean = re.sub('<br />', '\n', clean)
    return clean

def BuildMainDirectory():
    ########################################################
    ## Mode = None
    ## Build the main directory
    ########################################################
    
    items = [('Films', video_thumb, M_BROWSE),
             ('TV-Shows', tv_thumb, M_BROWSE),
             ('Short', video_thumb, M_BROWSE)]
        
    MediaItems = []
    for Title, Thumb, Mode in items:        
        Mediaitem = MediaItem()
        Mediaitem.Image = Thumb
        Mediaitem.Mode = Mode
        urlDict = cache.cacheFunction(GetUrlDict, None, Categories[Title])
        Url = BuildUrl(urlDict)        
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Url) + "&mode=" \
                        + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
    addDir(MediaItems)

    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
    
# Probably need to do different ones for TV shows
def Browse(Url):
    # set content type so library shows more views and info
    if 'TvShows' in Url:
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
    else:
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    
    MediaItems = GetItems(Url)
    
    # Add more menu items for browsing
    Menu = [('Genre', Url, programs_thumb, M_GENRES),
            ('Years', Url, topics_thumb, M_YEARS),
            ('Letter', Url, az_thumb, M_LETTERS),
            ('Sort', Url, added_thumb, M_SORT),
            ('Search', Url, search_thumb, M_SEARCH)]
    for Title, URL, Thumb, Mode in Menu:
        Mediaitem = MediaItem()
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(URL) + "&mode=" + str(Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setThumbnailImage(Thumb)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
    
    if MediaItems:        
        addDir(MediaItems)
    
    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
    ## Set Default View Mode. This might break with different skins. But who cares?
    SetViewMode()
    
def GetItems(Url):
    # Getting items, most likely is the same for all media types
    data = cache.cacheFunction(getURL, Url)
    if not data:
        return None
    data = data['html']
    Items = common.parseDOM(data, "div", {"class": "tvshow"})
    if not Items:
        return None
    
    MediaItems = []
    for Item in Items:
        divImg = common.parseDOM(Item, "div", {"class": "tvshow_img"})
        if not divImg:
            Image = ''
        else:
            divImg = divImg[0]
            Image = common.parseDOM(divImg, "img", ret="src")
            if not Image:
                Image = ''
            else:
                Image = Image[0]
                
        H3 = common.parseDOM(Item, "h3")
        if not H3:
            continue
        H3 = H3[0]
        Title = common.stripTags(H3)
        
        Href = common.parseDOM(H3, "a", ret="href")
        if not Href:
            continue
        Href = Href[0]
        
        Plot = common.parseDOM(Item, "div", {"style": "height: 78px; padding: 6px; overflow: hidden;"})
        if not Plot:
            Plot = ''
        else:
            Plot = Plot[0]
            
        Genres = common.parseDOM(Item, "a", {"class": "movies_genre"})
        Genre = ''
        if not Genres:
            Genre = ''
        else:
            for gen in Genres:
                Genre += gen + ', '
            Genre = Genre[:-2]
        
        Mediaitem = MediaItem()
        Mediaitem.Image = Image
        if 'TvShows' in Url:
            Mediaitem.Mode = M_TV
        else:
            Mediaitem.Mode = M_SOURCES       
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Href) + "&mode=" + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title, 'Plot': Plot, 'Genre': Genre})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
        
    # Next Page:
    pagination = common.parseDOM(data, "table", {"class": "pagination"})
    Next = None
    if pagination:
        pagination = pagination[0]
        Links = re.compile('href="(.+?)">(.+?)<').findall(pagination)
        for href, desc in Links:
            desc = desc.strip()
            if not desc == "&rsaquo;":
                continue
            Next = href
            break
    if Next:
        Mediaitem = MediaItem()
        Title = "Next"
        Url = BASE_URL + Next
        Mediaitem.Image = next_thumb
        Mediaitem.Mode = M_BROWSE
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
        
    return MediaItems

def GetSources(Url):
    # show sources
    data = cache.cacheFunction(getURL, Url)
    if not data:
        return
    data = data['html']
    catitem = common.parseDOM(data, "div", {"class": "cat_item"})
    if not catitem:
        return
    catitem = catitem[0]
    Sources = common.parseDOM(catitem, "div", {"class": "movie_link"})
    if not Sources:
        return
    MediaItems = []
    for Source in Sources:
        links = re.compile('href="(.+?)">(.+?)</a>').findall(Source)
        if not links:
            continue
        Href, Host = links[0]
        URL = BASE_URL + Href
        Title = Host
        
        Mediaitem = MediaItem()
        Mediaitem.Image = video_thumb
        Mediaitem.Mode = M_PLAY       
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(URL) + "&mode=" + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.ListItem.setProperty('IsPlayable', 'true')
        MediaItems.append(Mediaitem)
        
    addDir(MediaItems)
    
    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
        
def SeasonRoot(Url):
    # set content type so library shows more views and info
    xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
    data = cache.cacheFunction(getURL, Url)
    if not data:
        return
    data = data['html']
    catitem = common.parseDOM(data, "div", {"class": "cat_item"})
    if not catitem:
        return
    catitem = catitem[0]
    infoTable = common.parseDOM(catitem, "table", {"width": "100%", "border": "0", "cellspacing": "0",
                                                   "cellpadding": "1"})
    if not infoTable:
        Image = ''
    else:
        infoTable = infoTable[0]
        Image = common.parseDOM(infoTable, "img", ret="src")
        if not Image:
            Image = ''
        else:
            Image = Image[0]
    seasons = common.parseDOM(catitem, "div", {"class": "season season_\d"})
    MediaItems = []
    for season in seasons:
        h3 = common.parseDOM(season, "h3", {"class": "season_header"})
        if not h3:
            continue
        h3 = h3[0]
        Title = common.stripTags(h3)
        
        Mediaitem = MediaItem()
        Mediaitem.Image = Image
        Mediaitem.Mode = M_BROWSE_SEASON       
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
    
    addDir(MediaItems)
    
    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
    ## Set Default View Mode. This might break with different skins. But who cares?
    SetViewMode()
    
def SeasonEpisodes(Url, SeasonTitle):
    # set content type so library shows more views and info
    xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
    Season = re.compile('([\d]+)').findall(SeasonTitle)
    if not Season:
        Season = 0
    else:
        Season = Season[0]
    data = cache.cacheFunction(getURL, Url)
    if not data:
        return
    data = data['html']
    catitem = common.parseDOM(data, "div", {"class": "cat_item"})
    if not catitem:
        return
    catitem = catitem[0]
    infoTable = common.parseDOM(catitem, "table", {"width": "100%", "border": "0", "cellspacing": "0",
                                                   "cellpadding": "1"})
    if not infoTable:
        Image = ''
    else:
        infoTable = infoTable[0]
        Image = common.parseDOM(infoTable, "img", ret="src")
        if not Image:
            Image = ''
        else:
            Image = Image[0]
    seasons = common.parseDOM(catitem, "div", {"class": "season season_\d"})
    MediaItems = []
    for season in seasons:
        h3 = common.parseDOM(season, "h3", {"class": "season_header"})
        if not h3:
            continue
        h3 = h3[0]
        Title = common.stripTags(h3)
        
        if Title != SeasonTitle:
            continue
        
        episodes = re.compile('a class="episode".+?href="(.+?)".+?>Episode ([\d]*)<span class="episode_title"> - ([^<]+)').findall(season)
        for Url, Episode, Title in episodes:
            Date = ''
            if '(' in Title:
                split = Title.split('(', 1)
                Title = split[0].strip()
                dt = split[1].split(')', 1)[0].strip()
                Date = dt
                
            Mediaitem = MediaItem()
            Mediaitem.Image = Image
            Mediaitem.Mode = M_SOURCES       
            Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Title)
            Mediaitem.ListItem.setInfo('video', {'tvshowtitle': Title,
                                                 'episode': int(Episode),
                                                 'aired': Date,
                                                 'season': int(Season)})
            Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
            Mediaitem.ListItem.setLabel(Title)
            Mediaitem.Isfolder = True
            MediaItems.append(Mediaitem)
    
    addDir(MediaItems)
    
    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
    ## Set Default View Mode. This might break with different skins. But who cares?
    SetViewMode()
    
def GenresFolder(Url):
    key = 'Genre'
    Genres = ['Any', 'Action', 'Adult', 'Adventure', 'Animation', 'Biography', 'Comedy',
              'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'Film-Noir', 'Game-Show',
              'History', 'Horror', 'Music', 'Musical', 'Mystery', 'News', 'Reality-TV',
              'Romance', 'Sci-fi', 'Short', 'Sport', 'Talk-Show', 'Thriller', 'War', 'Western']
    FilterFolder(Url, key, Genres)
    
def LettersFolder(Url):
    key = 'Letter'
    Letters = ['Any']
    for i in string.uppercase[:26]:
        Letters.append(i)
    FilterFolder(Url, key, Letters)
    
def OrderFolder(Url):
    key = 'Sort'
    Items = ['LatestFirst', 'ByPopularity', 'OldestFirst']
    FilterFolder(Url, key, Items)
    
def YearsFolder(Url):
    key = 'Years'
    Items = ['2010-2012', '2000-2010', '1990-2000', '1980-1990', '1970-1980', '1960-1970',
             '1950-1960', '1940-1950', 'Any']
    for i in range(1989, 2013):
        Items.append(str(i))
    FilterFolder(Url, key, Items)
    
def FilterFolder(Url, key, Items):
    urlDict = cache.cacheFunction(GetUrlDict, Url)
    MediaItems = []
    for Item in Items:
        if Item == urlDict[key]:
            continue
        urlDict[key] = Item
        urlDict['Page'] = '1'
        Href = BuildUrl(urlDict)
        
        Mediaitem = MediaItem()
        Mediaitem.Mode = M_BROWSE
        Mediaitem.Image = programs_thumb
        Mediaitem.Url = sys.argv[0] + "?url=" + urllib.quote_plus(Href) + "&mode=" \
                        + str(Mediaitem.Mode) + "&name=" + urllib.quote_plus(Item)
        Mediaitem.ListItem.setInfo('video', { 'Title': Item})
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        Mediaitem.ListItem.setLabel(Item)
        Mediaitem.Isfolder = True
        MediaItems.append(Mediaitem)
    addDir(MediaItems)

    # End of Directory
    xbmcplugin.endOfDirectory(PluginHandle)
    
def Search(Url):
    keyb = xbmc.Keyboard('', 'Search Vidics.eu')
    keyb.doModal()
    if (keyb.isConfirmed() == False):
        return
    search = keyb.getText()
    if not search or search == '':
        return
    urlDict = cache.cacheFunction(GetUrlDict, Url)
    urlDict = cache.cacheFunction(GetUrlDict, None, urlDict['Category'])
    urlDict['Search'] = search
    URL = BuildUrl(urlDict)
    Browse(URL)

def Play(Url):
    ###########################################################
    ## Mode == M_PLAY
    ## Try to get a list of playable items and play it.
    ###########################################################
    data = cache.cacheFunction(getURL, Url)
    if not data:
        dialog = xbmcgui.Dialog()
        dialog.ok('Error', 'Error getting webpage.')
        xbmcplugin.setResolvedUrl(PluginHandle, False, xbmcgui.ListItem())
        return
    data = data['html']
    catitem = common.parseDOM(data, "div", {"class": "cat_item"})
    if not catitem:
        return
    catitem = catitem[0]
    Movie_Links = common.parseDOM(catitem, "div", {"class": "movie_link[\d]*"})
    if not Movie_Links:
        dialog = xbmcgui.Dialog()
        dialog.ok('Error', 'No Links Found.')
        xbmcplugin.setResolvedUrl(PluginHandle, False, xbmcgui.ListItem())
        return
    Movie_Link = Movie_Links[0]
    Href = common.parseDOM(Movie_Link, "a", ret="href")
    if not Href:
        return
    URL = Href[0]
    if not urlresolver.HostedMediaFile(URL).valid_url():
        dialog = xbmcgui.Dialog()
        dialog.ok('Error', 'Host is not supported.')
        xbmcplugin.setResolvedUrl(PluginHandle, False, xbmcgui.ListItem())
        return
    stream_url = urlresolver.HostedMediaFile(url=URL).resolve()
    xbmcplugin.setResolvedUrl(PluginHandle, True, xbmcgui.ListItem(path=stream_url))
    
# Set View Mode selected in the setting
def SetViewMode():
    try:
        # if (xbmc.getSkinDir() == "skin.confluence"):
        if Addon.getSetting('view_mode') == "1": # List
            xbmc.executebuiltin('Container.SetViewMode(502)')
        if Addon.getSetting('view_mode') == "2": # Big List
            xbmc.executebuiltin('Container.SetViewMode(51)')
        if Addon.getSetting('view_mode') == "3": # Thumbnails
            xbmc.executebuiltin('Container.SetViewMode(500)')
        if Addon.getSetting('view_mode') == "4": # Poster Wrap
            xbmc.executebuiltin('Container.SetViewMode(501)')
        if Addon.getSetting('view_mode') == "5": # Fanart
            xbmc.executebuiltin('Container.SetViewMode(508)')
        if Addon.getSetting('view_mode') == "6":  # Media info
            xbmc.executebuiltin('Container.SetViewMode(504)')
        if Addon.getSetting('view_mode') == "7": # Media info 2
            xbmc.executebuiltin('Container.SetViewMode(503)')
            
        if Addon.getSetting('view_mode') == "0": # Media info for Quartz?
            xbmc.executebuiltin('Container.SetViewMode(52)')
    except:
        print "SetViewMode Failed: " + Addon.getSetting('view_mode')
        print "Skin: " + xbmc.getSkinDir()


## Get Parameters
def get_params():
        param = []
        paramstring = sys.argv[2]
        if len(paramstring) >= 2:
                params = sys.argv[2]
                cleanedparams = params.replace('?', '')
                if (params[len(params) - 1] == '/'):
                        params = params[0:len(params) - 2]
                pairsofparams = cleanedparams.split('&')
                param = {}
                for i in range(len(pairsofparams)):
                        splitparams = {}
                        splitparams = pairsofparams[i].split('=')
                        if (len(splitparams)) == 2:
                                param[splitparams[0]] = splitparams[1]
        return param

def addDir(Listitems):
    if Listitems is None:
        return
    Items = []
    for Listitem in Listitems:
        Item = Listitem.Url, Listitem.ListItem, Listitem.Isfolder
        Items.append(Item)
    handle = PluginHandle
    xbmcplugin.addDirectoryItems(handle, Items)


'''if not os.path.exists(settingsDir):
    os.mkdir(settingsDir)
if not os.path.exists(cacheDir):
    os.mkdir(cacheDir)'''
                    
params = get_params()
url = None
name = None
mode = None

try:
        url = urllib.unquote_plus(params["url"])
except:
        pass
try:
        name = urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode = int(params["mode"])
except:
        pass

xbmc.log("Mode: " + str(mode))
#print "URL: " + str(url)
#print "Name: " + str(name)

if mode == None:
    BuildMainDirectory()
elif mode == M_DO_NOTHING:
    print 'Doing Nothing'
elif mode == M_BROWSE:
    Browse(url)
elif mode == M_SOURCES:
    GetSources(url)
elif mode == M_PLAY:
    Play(url)
elif mode == M_TV:
    SeasonRoot(url)
elif mode == M_BROWSE_SEASON:
    SeasonEpisodes(url, name)
elif mode == M_SEARCH:
    Search(url)
elif mode == M_GENRES:
    GenresFolder(url)
elif mode == M_YEARS:
    YearsFolder(url)
elif mode == M_LETTERS:
    LettersFolder(url)
elif mode == M_SORT:
    OrderFolder(url)
