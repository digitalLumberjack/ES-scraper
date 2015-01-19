ES-scraper
=====================
```
usage: scraper.py [-h] [-w pixels] [-t pixels] [-pisize] [-noimg] [-v] [-f]
                  [-crc] [-p] [-l]

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
  -crc        CRC scraping
  -p          partial scraping (per console)
  -l          i'm feeling lucky (use first result if the score is greater than 1)
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

