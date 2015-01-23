ES-scraper
=====================
```
usage: scraper.py [-h] [-w pixels] [-t pixels] [-pisize] [-noimg] [-v] [-f] [-p] [-l]
                  [-name name -platform name [-rompath path] [-ext extensions]]

ES-scraper, a scraper for EmulationStation

optional arguments:
  -h, --help  show this help message and exit
  -w pixels   defines a maximum width (in pixels) for boxarts (anything above
              that will be resized to that value)
  -t pixels   defines a maximum height (in pixels) for boxarts (anything above
              that will be resized to that value)
  -pisize     use best Raspberry Pi dimensions (375 x 350) for boxarts
  -noimg      disables boxart downloading
  -v          verbose output
  -f          force re-scraping (ignores and overwrites the current gamelist)
  -p          partial scraping (per console)
  -l          i'm feeling lucky (use first result if the score is greater than 1)
  -name       the "name" from es_settings.cfg - this sets the path for the gamelsit
              - must be used with platform option
              (ex: mame)
  -platform   Platform Name from http://www.emulationstation.org/gettingstarted.html 
              - must be used with name option
              (ex: arcade)
  -rompath    optional path to ROMs - if not supplied, rompath is build from name option
              - used with name and platform arguments
              (ex: ~/RetroPie/roms/mame)
  -ext        option extension list for ROMs - if not supplied, all files are matched
              - used with name and platform arguments
              (ex: ".zip .ZIP")
```

Quick script written in Python that uses various online sources to scrape artwork and game info and saves it as XML files to be read by EmulationStation.

For image resizing to work, you need to install PIL:
```
sudo apt-get install python-imaging
```

Usage
=====================
* If you haven't done so, please update ES before running this script.
* Run the script.

Examples:

on RetroPie, this is the easiest, fastest way to run the script
```
$ python scraper.py -pisize -l
```

same as above, but the script will prompt each ROM
```
$ python scraper.py -pisize
```

same as above, but the script will prompt for a single platform
```
$ python scraper.py -pisize -p
```

scrape /home/pi/RetroPie/roms/mame/*.(zip|ZIP) ROMS and scrape titles from the arcade platform
```
$ python scraper.py -pisize -name mame -platform arcade -ext ".zip .ZIP"
```
(use if issues parsing es_systems.cfg)

