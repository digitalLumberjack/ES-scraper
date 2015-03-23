#!/usr/bin/env python

import argparse
import difflib
import Image
import imghdr
import os
import re
import readline
import sys
import unicodedata
import urllib
import urllib2
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
import zlib
import glob

SCUMMVM = False
arcaderoms = {}

parser = argparse.ArgumentParser(description='ES-scraper, a scraper for EmulationStation')
parser.add_argument("-w", metavar="pixels", help="defines a maximum width (in pixels) for boxarts (anything above that will be resized to that value)", type=int)
parser.add_argument("-t", metavar="pixels", help="defines a maximum height (in pixels) for boxarts (anything above that will be resized to that value)", type=int)
parser.add_argument("-pisize", help="use best Raspberry Pi dimensions (375 x 350) for boxarts", action='store_true')
parser.add_argument("-noimg", help="disables boxart downloading", action='store_true')
parser.add_argument("-v", help="verbose output", action='store_true')
parser.add_argument("-f", help="force re-scraping (ignores and overwrites the current gamelist)", action='store_true')
parser.add_argument("-p", help="partial scraping (per console)", action='store_true')
parser.add_argument("-l", help="i'm feeling lucky (use first result)", action='store_true')
parser.add_argument("-name", help="manually specify a name, ignore es_settings.cfg (must be used with -platform)", type=str)
parser.add_argument("-rompath", help="manually specify a path, ignore es_settings.cfg (used with -name and -platform)", type=str)
parser.add_argument("-platform", help="manually specify a platform for ROMs in 'rompath', ignore es_settings.cfg (must be used with -name", type=str)
parser.add_argument("-ext", help="manually specify extensions for 'rompath', ignore es_settings.cfg (used with -name and -platform)", type=str)
args = parser.parse_args()

# URLs for retrieving from TheGamesDB API
GAMESDB_BASE  = "http://thegamesdb.net/api/"
PLATFORM_URL  = GAMESDB_BASE + "GetPlatform.php"
GAMEINFO_URL  = GAMESDB_BASE + "GetGame.php"
GAMESLIST_URL = GAMESDB_BASE + "GetGamesList.php"

DEFAULT_WIDTH  = 375
DEFAULT_HEIGHT = 350

gamesdb_platforms = {}

# Used to signal user wants to manually define title from results
class ManualTitleInterrupt(Exception):
    pass
class ManualAllPlatformInterrupt(Exception):
    pass

def normalize(s):
   return ''.join((c for c in unicodedata.normalize('NFKD', unicode(s)) if unicodedata.category(c) != 'Mn'))

def fixExtension(file):
    newfile = "%s.%s" % (os.path.splitext(file)[0],imghdr.what(file))
    os.rename(file, newfile)
    return newfile

def getPlatforms():
    platforms = ET.parse('./TheGameDbPlatforms.xml')
    platformsroot = platforms.getroot()
    for platform in platformsroot:
        gamesdb_platforms[platform.find('es').text] = platform.find('db').text

def getArcadeRomNames():
    fbafile=open("./fba2x.txt")
    lines=fbafile.read().splitlines()
    for line in lines:
        m = re.search('^\| +([^ ]+) *\|[^|]*\| +([^|]+?) +\|.*$',line)
        if m:
            #print "%s - %sxxx" % (m.groups()[0], m.groups()[1])
            arcaderoms[m.groups()[0]] = m.groups()[1]
    fbafile.close()
    
    mamefile=open("./mame4all.txt")
    lines=mamefile.read().splitlines()
    for line in lines:
        m = re.search('([^ ]+)\s+"(.+)"',line)
        if m:
            #print "%s - %s" % (m.groups()[0], m.groups()[1])
            arcaderoms[m.groups()[0]] = m.groups()[1]
    mamefile.close()
    
def readConfig(file):
    systems=[]
    config = ET.parse(file)
    configroot = config.getroot()
    for child in configroot.findall('system'):
        nameElement = child.find('name')
        pathElement = child.find('path')
        platformElement = child.find('platform')
        extElement = child.find('extension')
        if nameElement is not None and pathElement is not None and platformElement is not None and extElement is not None:
            name = nameElement.text
            path = re.sub('^~', homepath, pathElement.text, 1)
            ext = extElement.text
            platform = platformElement.text
            numfiles = len(glob.glob(path+'/**'))
            if numfiles > 0:
                system=(name,path,ext,platform)
                systems.append(system)
        if args.v:
            print "SYSTEM:"
            if nameElement is not None:
                print "  Name: %s" % nameElement.text
            else:
                print "  Name: <missing>"
            if pathElement is not None:
                print "  Path: %s" % re.sub('^~', homepath, pathElement.text, 1)
            else:
                print "  Path: <missing>"
            if platformElement is not None:
                print "  Platform: %s" % platformElement.text
            else:
                print "  Platform: <missing>"
            if extElement is not None:
                print "  Ext: %s" % extElement.text
            else:
                print "  Ext: <missing>"
            print "  Potential ROMs: %s" % str(numfiles)
                
    return systems

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def exportList(gamelist, gamelist_path):
    if gamelistExists and args.f is False:
        for game in gamelist.iter("game"):
            existinglist.getroot().append(game)

        indent(existinglist.getroot())
        ET.ElementTree(existinglist.getroot()).write(gamelist_path,short_empty_elements=False)
        print "Done! %s updated." % gamelist_path
    else:
        indent(gamelist)
        ET.ElementTree(gamelist).write(gamelist_path,short_empty_elements=False)
        print "Done! List saved on %s" % gamelist_path

def getPlatformGameLists(platforms):
    gamelists = []
    for (i, platform) in enumerate(platforms):
        gamelist = urllib2.Request(GAMESLIST_URL, urllib.urlencode({'platform' : platform}),
                               headers={'User-Agent' : "RetroPie Scraper Browser"})
        gamelists.append(ET.parse(urllib2.urlopen(gamelist)).getroot())
    return gamelists

def getGameInfo(file, platforms, gamelists):
    title = re.sub(r'\[.*?\]|\(.*?\)', '', os.path.splitext(os.path.basename(file))[0]).strip()
    options = []

    def stripRegionStrings(title):
        # Strip out parens
        title = re.sub('(\(.*?\))', '', title)
        return title

    def getAllPlatformTitle(title):
        gamelist = urllib2.Request(GAMESLIST_URL, urllib.urlencode({'name' : title}),
                               headers={'User-Agent' : "RetroPie Scraper Browser"})
        platformgamelist = ET.parse(urllib2.urlopen(gamelist)).getroot()
        return getTitleOptions(title, platformgamelist.findall('Game'))
        
    def getTitleOptions(title, results):
        options = []
        ch_exclude = set(',:&!')
        common_words = ['in','of','the','and','to','a','-']

        scrubbed_title = stripRegionStrings(title)
        scrubbed_title = ''.join(ch for ch in scrubbed_title if ch not in ch_exclude)

        word_list = filter(lambda x: x.lower() not in common_words, scrubbed_title.split() )

        for i,v in enumerate(results):
            check_title = getTitle(v)
            check_title_2 = check_title.replace('-', ' ')
            scrubbed_check = ''.join(ch for ch in check_title if ch not in ch_exclude)

            check_word_list = filter(lambda x: x.lower() not in common_words \
                                        and len(x) > 2, scrubbed_check.split() )

            # Generate rank based on how many substring matches occurred.
            game_rank = 0

            # - Give perfect (100) rank to titles that match exactly
            if title.lower() == check_title.lower() \
                    or title.lower() == check_title.replace('-', '').lower() \
                    or title.lower() == check_title_2.lower():
                game_rank = 100
            # - Give high (99) rank to title if same words appear in result
            #   (e.g.  "The Legend of Zelda" --> "Legend of Zelda, The"
            elif sorted(word_list) == sorted(check_word_list):
                game_rank = 99
            # - Give high (95) rank to titles that appear entirely in results
            elif title.lower() in check_title.lower() \
                    or title.lower() in check_title.replace('-', '').lower() \
                    or title.lower() in check_title_2.lower():
                game_rank = 95
            # - Otherwise, rank title by number of occurrences of words
            else:
                #print "%s" % '|'.join(word_list)
                game_rank = len( re.findall("(%s)" % '|'.join(word_list), check_title, re.IGNORECASE) )
            if game_rank:
                options.append((game_rank, getTitle(v), getGamePlatform(v), getId(v)))
        return options

    for (i, platform) in enumerate(platforms):
        # Retrieve full game data using ID
        if platform == "Arcade" : title = getRealArcadeTitle(title)	
        results = gamelists[i].findall('Game')

        # Search for matching title options
        if len(results) > 1:
            options.extend(getTitleOptions(title, results))


    options = sorted(options, key=lambda x: (-x[0], x[1]))

    result = None
    while not result:
        # * I'm feeling lucky - select first result
        if args.l:
            if not options:     # If no options available, return None
                return None
            if options[0][0] == 1:
                print "match not high enough"
                return None
            else:
                result = options[0]
            continue

        try:
            choice = chooseResult(options)
            if choice is None:
                print "Skipping game..."
                return None
            result = options[choice]
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except ManualTitleInterrupt:
            # Allow user to re-enter name of game title (manual search)
            readline.set_startup_hook(lambda: readline.insert_text(title))
            try:
                new_title = raw_input("Enter new title: ")
            finally:
                readline.set_startup_hook()
            print " ~ Searching for '%s' [%s]..." % (new_title, os.path.basename(file))
            options = []
            for (i, platform) in enumerate(platforms):
                results = gamelists[i].findall('Game')
                options.extend(getTitleOptions(new_title, results))
            options = sorted(options, key=lambda x: (-x[0], x[1]))
        except ManualAllPlatformInterrupt:
            # Allow user to re-enter name of game title and perform search of all platforms
            readline.set_startup_hook(lambda: readline.insert_text(title))
            try:
                new_title = raw_input("Enter new title: ")
            finally:
                readline.set_startup_hook()
            print " ~ Searching for '%s' [%s]..." % (new_title, os.path.basename(file))
            options = sorted(getAllPlatformTitle(new_title), key=lambda x: (-x[0], x[1]))
            
        except Exception as e:
            print "Invalid selection (%s) " % e

    try:
        gamereq = urllib2.Request(GAMEINFO_URL, urllib.urlencode({'id': result[3], 'platform' : result[2]}),
                                  headers={'User-Agent' : "RetroPie Scraper Browser"})
        remotedata = urllib2.urlopen( gamereq )
        data = ET.parse(remotedata).getroot()
    except ET.ParseError:
        print "Malformed XML found, skipping game.. (source: {%s})" % URL
        return None
    return data.find("Game")

def getText(node):
    return normalize(node.text) if node is not None else None

def getId(nodes):
    return getText(nodes.find("id"))

def getTitle(nodes):
    return getText(nodes.find("GameTitle"))

def getGamePlatform(nodes):
    return getText(nodes.find("Platform"))

def getScummvmTitle(title):
    print "Fetching real title for %s from scummvm.org" % title
    URL  = "http://scummvm.org/compatibility/DEV/%s" % title.split("-")[0]
    data = "".join(urllib2.urlopen(URL).readlines())
    m    = re.search('<td>(.*)</td>', data)
    if m:
       print "Found real title %s for %s on scummvm.org" % (m.group(1), title)
       return m.groups()[0]
    else:
       print "No title found for %s on scummvm.org" % title
       return title

def getRealArcadeTitle(title):
    print "%s found title: %s" % (title, arcaderoms[title])
    return arcaderoms[title]

def getDescription(nodes):
    return getText(nodes.find("Overview"))

def getImage(nodes):
    return getText(nodes.find("Images/boxart[@side='front']"))

def getRelDate(nodes):
    return getText(nodes.find("ReleaseDate"))

def getPublisher(nodes):
    return getText(nodes.find("Publisher"))

def getDeveloper(nodes):
    return getText(nodes.find("Developer"))

def getRating(nodes):
    return getText(nodes.find("Rating"))

def getGenres(nodes):
    genres = []
    if nodes.find("Genres") is not None:
        for item in nodes.find("Genres").iter("genre"):
            genres.append(item.text)

    return genres if len(genres)>0 else None

def getPlayers(nodes):
    return getText(nodes.find('Players'))

def resizeImage(img, output):
    maxWidth = args.w
    maxHeight = args.t
    if img.size[0] > maxWidth or img.size[1] > maxHeight:
        if img.size[0] > maxWidth:
            print "Boxart over %spx (width). Resizing boxart.." % maxWidth
        elif img.size[1] > maxHeight:
            print "Boxart over %spx (height). Resizing boxart.." % maxHeight
        img.thumbnail((maxWidth, maxHeight), Image.ANTIALIAS)
        img.save(output)

def downloadBoxart(path, output):
    os.system("wget -q http://thegamesdb.net/banners/%s --output-document=\"%s\"" % (path,output))

def skipGame(list, filepath):
    for game in list.iter("game"):
        if game.findtext("path") == filepath:
            if args.v:
                print "Game \"%s\" already in gamelist. Skipping.." % os.path.basename(filepath)
            return True

def chooseResult(options):
    if len(options) > 0:
        count = 0
        for i, v in enumerate(options):
            rank  = v[0]
            title = v[1]
            platform = v[2]
            try:
                print " [%s] %s [%s]  (+%s)" % (i, title, platform, rank)
            except Exception as e:
                print "Exception! %s %s" % (e, title)
            count += 1
            if count >= 40:
                print "    ... Limiting to top 40 results (of %s) ..." % len(options)
                break
        print " [r] -> Enter new title to search"
        print " [a] -> Search all platforms for title"
        choice = raw_input("Select a result (or press Enter to skip): ")
        if choice in ['r', 'R']:
            raise ManualTitleInterrupt
        if choice in ['a', 'A']:
            raise ManualAllPlatformInterrupt
        if not choice and choice != "0":
            return None
        return int(choice)
    else:
        print "* No options found. "
        choice = raw_input("Enter 'r' to search alternate title, 'a' to search all platforms, or press Enter to skip): ")
        if choice in ['r', 'R']:
            raise ManualTitleInterrupt
        if choice in ['a', 'A']:
            raise ManualAllPlatformInterrupt
        if not choice and choice != "0":
            return None
        raise ValueError


def autoChooseBestResult(nodes,t):
    results = nodes.findall('Game')
    t = t.split('(', 1)[0]
    if len(results) > 1:

        sep = ' |' # remove platform name
        lista = []
        listb = []
        listc = []
        for i,v in enumerate(results): # Do it backwards to eliminate false positives
            a = (str(getTitle(v).split(sep, 1)[0]).split('(', 1)[0])
            lista.append(a)
            listb.append(i)
        listc = list(lista)
        listc.sort(key=len)
        x = 0
        for n in reversed(listc):
            s = difflib.SequenceMatcher(None, t, lista[lista.index(n)]).ratio()
            if s > x:
                x = s
                xx = lista.index(n)
        ss = int(x * 100)
        print "Game Title Found  " + str(ss) + "% Chance : " + lista[xx]
        return xx
    else:
        return 0


def getPlatformNames(_platforms):
    platforms = _platforms.split(',')
    for (i, platform) in enumerate(platforms):
        if gamesdb_platforms[platform] is not None: platforms[i] = gamesdb_platforms[platform]
    return platforms


def scanFiles(SystemInfo):
    name = SystemInfo[0]
    emulatorname = name
    if name == "scummvm":
        global SCUMMVM
        SCUMMVM = True
    folderRoms = SystemInfo[1]
    extension = SystemInfo[2]
    platforms = getPlatformNames(SystemInfo[3])

    global gamelistExists
    global existinglist
    gamelistExists = False

    gamelist = Element('gameList')
    folderRoms = os.path.expanduser(folderRoms)

    destinationFolder = folderRoms;
    try:
        os.chdir(destinationFolder)
    except OSError as e:
        print "%s : %s" % (destinationFolder, e.strerror)
        return

    platform_gamelists = getPlatformGameLists(platforms)

    print "Scanning folder..(%s)" % folderRoms
    gamelist_path = gamelists_path+"%s/gamelist.xml" % emulatorname

    if os.path.exists(gamelist_path):
        try:
            existinglist = ET.parse(gamelist_path)
            gamelistExists=True
            if args.v:
                print "Gamelist already exists: %s" % gamelist_path
        except:
            gamelistExists = False
            print "There was an error parsing the list or file is empty"

    for root, dirs, allfiles in os.walk(folderRoms, followlinks=True):
        allfiles.sort()
        for files in allfiles:
            if extension=="" or files.endswith(tuple(extension.split(' '))):
                try:
                    filepath = os.path.abspath(os.path.join(root, files))
                    filepath = filepath.replace(folderRoms, ".")
                    filename = os.path.splitext(files)[0]

                    if gamelistExists and not args.f:
                        if skipGame(existinglist,filepath):
                            continue

                    print "\nTrying to identify %s.." % files

                    data = getGameInfo(filepath, platforms, platform_gamelists)

                    if data is None:
                        continue
                    else:
                        result = data

                    str_id = getId(result)
                    str_title = getTitle(result)
                    str_des = getDescription(result)
                    str_img = getImage(result)
                    str_rd = getRelDate(result)
                    str_pub = getPublisher(result)
                    str_dev = getDeveloper(result)
                    str_rating = getRating(result)
                    str_players = getPlayers(result)
                    lst_genres = getGenres(result)

                    if str_title is not None:
                        game = SubElement(gamelist, 'game')
                        id = SubElement(game, 'id')
                        path = SubElement(game, 'path')
                        name = SubElement(game, 'name')
                        desc = SubElement(game, 'desc')
                        image = SubElement(game, 'image')
                        releasedate = SubElement(game, 'releasedate')
                        publisher = SubElement(game, 'publisher')
                        developer = SubElement(game, 'developer')
                        rating = SubElement(game, 'rating')
                        players = SubElement(game, 'players')
                        genres = SubElement(game, 'genres')
                        region = SubElement(game, 'region')
                        romtype = SubElement(game, 'romtype')
			region.text = ""
			romtype.text = "official" 
                        id.text = str_id
                        path.text = filepath
                        name.text = str_title
                        print "Game Found: %s [%s]" % (str_title, getGamePlatform(result))

                    if str_des is not None:
                        desc.text = str_des

                    if str_img is not None and args.noimg is False:
                        # Store boxart in a boxart/ folder (create if needed)

                        if not os.path.exists(boxart_path + "%s" % emulatorname):
                            os.mkdir(boxart_path + "%s" % emulatorname)

                        imgpath = boxart_path + "%s/%s-image%s" % (emulatorname, filename,os.path.splitext(str_img)[1])

                        print "Downloading boxart.."

                        downloadBoxart(str_img,imgpath)
                        imgpath = fixExtension(imgpath)
                        image.text = imgpath

                        if args.w or args.t:
                            try:
                                resizeImage(Image.open(imgpath), imgpath)
                            except Exception as e:
                                print "Image resize error"
                                print str(e)

                    if str_rd is not None:
                        releasedate.text = str_rd

                    if str_pub is not None:
                        publisher.text = str_pub

                    if str_dev is not None:
                        developer.text = str_dev

                    if str_rating is not None:
                        flt_rating = float(str_rating)
                        rating.text = "%.6f" % flt_rating
                    else:
                        rating.text = "0.000000"

                    if str_players is not None:
                        players.text = str_players

                    if lst_genres is not None:
                        for genre in lst_genres:
                            newgenre = SubElement(genres, 'genre')
                            newgenre.text = genre.strip()
                except KeyboardInterrupt:
                    print "Ctrl+C detected. Closing work now..."
                    break
                except Exception as e:
                    print "Exception caught! %s" % e

    if gamelist.find("game") is None:
        print "No new games added."
    else:
        print "{} games added.".format(len(gamelist))
        exportList(gamelist, gamelist_path)





if os.getuid() == 0:
    username = os.getenv("SUDO_USER")
    homepath = os.path.expanduser('~'+username+'/')
else:
    homepath = os.path.expanduser('~')

essettings_path = homepath + "/.emulationstation/es_systems.cfg"
gamelists_path = homepath + "/.emulationstation/gamelists/"
boxart_path = homepath + "/.emulationstation/downloaded_images/"


if args.name and args.platform:

    if args.rompath:
        rompath = args.rompath
    else:
        rompath = homepath+"/RetroPie/roms/"+args.name

    if args.ext:
        ext = args.ext
    else:
        ext = ""
    
    ES_systems = [(args.name,rompath,ext,args.platform)]
    
else:

    if not os.path.exists(essettings_path):
        essettings_path = "/etc/emulationstation/es_systems.cfg"

    try:
        config=open(essettings_path)
    except IOError as e:
        sys.exit("Error when reading config file: %s \nExiting.." % e.strerror)

    ES_systems = readConfig(config)




getPlatforms()
getArcadeRomNames()
print parser.description

if args.pisize:
    print "Using Raspberry Pi boxart size: (%spx x %spx)" % (DEFAULT_WIDTH, DEFAULT_HEIGHT)
    args.w = DEFAULT_WIDTH
    args.t = DEFAULT_HEIGHT
else:
    if args.w:
        print "Max width set: %spx." % str(args.w)
        args.t = args.t if args.t else 999999
    if args.t:
        print "Max height set: %spx." % str(args.t)
        args.w = args.w if args.w else 999999
if args.noimg:
    print "Boxart downloading disabled."
if args.f:
    print "Re-scraping all games.."
if args.v:
    print "Verbose mode enabled."
if args.p:
    print "Partial scraping enabled. Systems found:"
    for i,v in enumerate(ES_systems):
        print "[%s] %s" % (i,v[0])
    try:
        var = int(raw_input("System ID: "))
        scanFiles(ES_systems[var])
    except:
        sys.exit()
else:
    for i,v in enumerate(ES_systems):
        scanFiles(ES_systems[i])

print "All done!"

