import numpy 
import re
import csv
import requests
from bs4 import BeautifulSoup
import json


def parse(web, weird, site):
    global Empty
    global Error404
    global Http_error
    global empty_counter
    global error404_counter
    global httperror_counter

    # Requests the target web
    try:
        weird_current=False
        page = requests.get(web,timeout=3)
        page.raise_for_status()
        # Checks if it is empty
        if page.content=="":
            print "empty"
        # Checks if it contains error 404 
        elif "HTTP Error 404" in page.content:
            print "error 404"
        else:
            print "no errors"
    
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)   
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        



url="http://robowiki.net/wiki/Robocode/Console_Usage"
# user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36'
# headers = {'User-Agent': user_agent}
template_api="http://web.archive.org/cdx/search/cdx?url="
page = requests.get(template_api+url)

#print page.content
# print page.status_code



#result = re.findall("20\d{10,14}", page)

#print result

# result = re.search('<!-- NEXT/PREV MONTH NAV AND MONTH INDICATOR -->(.*)<!-- NEXT/PREV CAPTURE NAV AND DAY OF MONTH INDICATOR -->', page.text)
# print(result.group(1))
    
#page=requests.get("https://web.archive.org/web/20180404104423/http://robowiki.net:80/wiki/RoboWiki:Users",timeout=3)
# if "<!-- start content -->" in page.content:
#     print "solved"
# else:
#     print "nope!"
    
# # Passing the source code to BeautifulSoup to create a BeautifulSoup object for it.
# soup = BeautifulSoup(page.text, 'lxml')
# # Extracting all the <a> tags into a list.
# tags = soup.find_all('a')
# # Iterates over all the child pages and recursively parses them if they are not empty, contain ".html", and they have not been visited before
# for tag in tags:
#     print tag.get('href')