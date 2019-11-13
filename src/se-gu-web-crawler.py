'''
Created on 5 Nov 2019
@Description: web crawler script which looks for empty files and files only containing "44" in 
@author: gsergio
'''

from bs4 import BeautifulSoup
import requests
import sys
import csv
import re
import time
from test import template_api
sys.setrecursionlimit(2000)

# Helper class to measure computation time
class Timer(object):
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        if self.name:
            print('[%s]' % self.name,)
        print 'Elapsed: %.2f seconds' % (time.time() - self.tstart)


############Global variables
first_web="http://www.cse.chalmers.se/~bergert/robowiki-mirror/RoboWiki/robowiki.net/wiki/Main_Page.html"
template="http://www.cse.chalmers.se/~bergert/robowiki-mirror/RoboWiki/robowiki.net/wiki/"
template_robowiki="http://robowiki.net/wiki/"
template_api="http://web.archive.org/cdx/search/cdx?url="
template_archive="https://web.archive.org/web/"
connection_errors=list()

timeout_errors=list()
visited=list()

# Matrixes of errors
Exception_error=None
Timeout_error=None
Http_error=None
Empty=None
Error404=None
Fixed=None

# error counters
empty_counter=0
error404_counter=0
httperror_counter=0
timeout_counter=0
exception_counter=0
n_pages=0
fixed_counter=0

# Do we need to crawl the webs or only to read the text files?
CRAWL=False
FIX=True


def init():
    global Empty
    global Error404
    global Http_error
    global Exception_error
    global Timeout_error
    global Fixed
    # 2000 x 4 matrixes. 
    # Row 0: empty or erroneous url from the mirror
    # Row 1: whether there is a weird "../" char on the 1st row
    # Row 2: adapted url to the website
    # Row 3: whether the adapted url is also empty or erroneous
    # Row 4: adapted url to the web archive
    # Row 5: whether the adapted url is also empty or erroneous
    Empty = [[False for x in range(20000)] for x in range(6)] 
    Error404 = [[False for x in range(20000)] for x in range(6)] 
    Http_error = [[False for x in range(100000)] for x in range(6)] 
    Exception_error = [[False for x in range(20000)] for x in range(6)] 
    Timeout_error = [[False for x in range(20000)] for x in range(6)] 

    # Fixed urls
    # Row 0: original url, empty or erroneous (from mirror)
    # Row 1: working url, either from the website or the archive
    Fixed = [[False for x in range(100000)] for x in range(2)] 
    

# Writes the empty and erroneous urls into text files
def write_responses(file, matrix, counter):
    if file=="fixed":
        f = open("files/"+file+".csv", "a")
    else:
        f = open("files/"+file+".csv", "w")
        f.write("mirror|weird|adapted_url|adapted_url_correct|adapted_url_archive|adapted_url_archive_correct"+"\n")
    for line in range(counter):
        for i in range(len(matrix)):
            if i > 0:
                f.write("|"+str(matrix[i][line]))
            else:
                f.write(str(matrix[i][line]))
        f.write("\n")
    f.close()

def read_files(file, matrix):      
    with open("files/"+file+".csv", mode='r') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter='|')
        row_count = sum(1 for iter in csv_reader)
        for i in range(len(matrix)):
            matrix[i]=matrix[i][0:row_count-1]  
    with open("files/"+file+".csv", mode='r') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter='|')   
        line_count = 0
        for row in csv_reader:
            if line_count > 0:
                for i in range(len(matrix)):
                    matrix[i][line_count-1]=row[i]
            line_count=line_count+1
    return matrix, line_count-1

def adapt_urls(matrix):
    i=0
    for i in range(len(matrix[0])):
        url=matrix[0][i]
        url=url.replace(template, template_robowiki)
        url = re.sub("index.*\.html\?", "index.php?", url)
        url=url.replace("RoboWiki_", "RoboWiki:")
        url=url.replace("Special_", "Special:")
        url=url.replace("Category_", "Category:")
        url=url.replace("User_", "User:")
        url=url.replace("File_", "File:")
        url=url.replace("Category_", "Category:")
        url=url.replace("Talk_", "")
        url=url.replace("talk_", "")
        if url.endswith(".html"):
            url=url[:-5]
        matrix[2][i]=url
    return matrix

def reset_counters():
    global empty_counter
    global error404_counter
    global httperror_counter
    global timeout_counter
    global exception_counter
    #Store lengths of files
    length_empty_links=empty_counter
    lenght_error404_links=error404_counter
    httperror=httperror_counter
    timeout=timeout_counter
    exception=exception_counter
    #Reset counters for second phase
    empty_counter=0
    error404_counter=0
    httperror_counter=0
    timeout_counter=0
    exception_counter=0
    return length_empty_links, lenght_error404_links, httperror #, timeout, exception
    
# Put all the fixed links into one matrix
def add_fixed(matrix, site):    
    global Fixed
    global fixed_counter
    index_remove=list()
    if site=="website":
        for i in range(len(matrix[3])):
            if matrix[3][i]=="False":
                Fixed[0][fixed_counter]=matrix[0][i]
                Fixed[1][fixed_counter]=matrix[2][i]
                index_remove.append(i)
                fixed_counter=fixed_counter+1
    elif site=="archive":
        for i in range(len(matrix[5])):
            if matrix[5][i]=="False":
                Fixed[0][fixed_counter]=matrix[0][i]
                Fixed[1][fixed_counter]=matrix[4][i]
                index_remove.append(i)
                fixed_counter=fixed_counter+1
    for i in reversed(index_remove):
        for j in range(len(matrix)): 
            del matrix[j][i] 
    return matrix, len(matrix[3])
            
def crawl_webarchive(matrix):
    for i in range(len(matrix[2])):
        matrix[4][i], matrix[5][i]=parse_webarchive(matrix[2][i])
        if matrix[5][i] == False:
            print "fixed website! "+matrix[4][i]
        else:
            print "no possible fix for this website! ("+matrix[5][i]+")"    
    return matrix, len(matrix[3])       
        
def parse_webarchive(url):
    search=requests.get(template_api+url)
    #here I need to get the timestamps of the snapshots using regex search.content
    timestamps = re.findall("20\d{10,14}", search.content)
    if len(timestamps)>0:
        for timestamp in timestamps:
            page_return=template_archive+timestamp+"/"+url
            try:
                page = requests.get(template_archive+timestamp+"/"+url,timeout=3)
                #print template_archive+timestamp+"/"+url
                page.raise_for_status()
                # Checks if it is empty
                if "<!-- start content -->" in page.content:
                    return page.url, False       
                else:
                    print "empty or erroneous page, let's try next" 
                    error="empty"  
                    page_return=page.url
            except requests.exceptions.HTTPError as errh:      
                error="http-error"
            except requests.exceptions.ConnectionError as errc:
                error="connection-error"
            except requests.exceptions.Timeout as errt:
                error="timeout-error"
            except requests.exceptions.RequestException as err:
                error="exception-error"
        return page_return, error
    else:
        return "None", "Not recorded"  
     
    
def update_matrix(matrix, web, weird, counter, site, problem):
    if site=="mirror":
        matrix[0][counter]=web
        if weird:
            matrix[1][counter]=True
        counter=counter+1
    elif site=="website":
        matrix[3][counter]=problem
    elif site=="archive":
        matrix[5][counter]=True
    return matrix, counter

# Method in charge of parsing the given url
def parse(web, weird, site, matrix):
    global Empty
    global Error404
    global Http_error
    global Exception_error
    global Timeout_error
    global empty_counter
    global error404_counter
    global httperror_counter
    global timeout_counter
    global exception_counter

    # Requests the target web
    try:
        weird_current=False
        page = requests.get(web,timeout=3)
        page.raise_for_status()
        # Checks if it is empty
        if page.content=="":       
            if site=="website":
                if matrix=="empty":
                    Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "empty")
                elif matrix=="error404":
                    Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "empty")
                elif matrix=="httperror":
                    Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "empty")
                elif matrix=="timeout":
                    Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "empty")
                elif matrix=="exception":
                    Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "empty")
            else:
                Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "empty")
        # Checks if it contains error 404 
        elif "HTTP Error 404" in page.content:
            if site=="website":
                if matrix=="empty":
                    Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "error 404")
                elif matrix=="error404":
                    Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "error 404")
                elif matrix=="httperror":
                    Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "error 404")
                elif matrix=="timeout":
                    Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "error 404")
                elif matrix=="exception":
                    Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "error 404")
            else:
                Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "error 404")
        else:
            # Extracting the source code of the page.
            data = page.text  
            # Passing the source code to BeautifulSoup to create a BeautifulSoup object for it.
            soup = BeautifulSoup(data, 'lxml')
            # Extracting all the <a> tags into a list.
            tags = soup.find_all('a')
            # Iterates over all the child pages and recursively parses them if they are not empty, contain ".html", and they have not been visited before
            for tag in tags:
                if (site=="mirror") and (tag.get('href') != None) and (".html" in tag.get('href')):
                    if "../" in tag.get('href') and not "/w/" in tag.get('href'):
                        helper=tag.get('href').replace("../", "")
                        weird_current=True
                    else:
                        helper=tag.get('href')
                    if "/wiki/wiki" in template+helper:
                        if helper.startswith('wiki'):
                            helper=helper[5:]
                    if (not(helper in visited)):
                        #print(template+helper)
                        visited.append(helper)
                        parse(template+helper, weird_current, "mirror", "mirror")    
    
    except requests.exceptions.HTTPError as errh:      
        #print ("Http Error:",errh)
        if site=="website":
            if matrix=="empty":
                Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "http error")
            elif matrix=="error404":
                Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "http error")
            elif matrix=="httperror":
                Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "http error")
            elif matrix=="timeout":
                Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "http error")
            elif matrix=="exception":
                Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "http error")
        else: 
            Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "http error")
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        connection_errors.append(web)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)   
        if site=="website":
            if matrix=="empty":
                Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "timeout error")
            elif matrix=="error404":
                Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "timeout error")
            elif matrix=="httperror":
                Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "timeout error")
            elif matrix=="timeout":
                Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "timeout error")
            elif matrix=="exception":
                Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "timeout error")
        else: 
            Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "timeout error")
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        if site=="website":
            if matrix=="empty":
                Empty, empty_counter=update_matrix(Empty, web, weird, empty_counter, site, "exception error")
            elif matrix=="error404":
                Error404, error404_counter=update_matrix(Error404, web, weird, error404_counter, site, "exception error")
            elif matrix=="httperror":
                Http_error, httperror_counter=update_matrix(Http_error, web, weird, httperror_counter, site, "exception error")
            elif matrix=="timeout":
                Timeout_error, timeout_counter=update_matrix(Timeout_error, web, weird, timeout_counter, site, "exception error")
            elif matrix=="exception":
                Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "exception error")
        else:
            Exception_error, exception_counter=update_matrix(Exception_error, web, weird, exception_counter, site, "exception error")

if __name__ == '__main__': 
    init()
    if CRAWL:
        with Timer('calculation-mirror'):
            parse(first_web, False, "mirror", "")
        write_responses("empty_links", Empty, empty_counter)
        write_responses("error404_links", Error404, error404_counter)
        write_responses("Http_error", Http_error, httperror_counter)
        write_responses("timeout_error", Timeout_error, timeout_counter)
        write_responses("exception_error", Exception_error, exception_counter)
    else:
        Empty, empty_counter=read_files("empty_links", Empty)
        Error404, error404_counter=read_files("error404_links", Error404)
        Http_error, httperror_counter=read_files("Http_error", Http_error)
#         Timeout_error, timeout_counter=read_files("timeout_error", Timeout_error)
#         Exception_error, exception_counter=read_files("exception_error", Exception_error)
    print "Empty pages: "+str(empty_counter)
    print "Error 404 pages: "+str(error404_counter)
    print "Http error pages: "+str(httperror_counter)
#     print "Timeout error pages: "+str(timeout_counter)
#     print "Exception error pages: "+str(exception_counter)
    
    print "------------------------"
    # Adapt urls (to website) and write them down 
    Empty=adapt_urls(Empty) 
    print "Empty pages urls have been adapted"
    #write_responses("length_empty_links_parsed", Empty, empty_counter)
    Error404=adapt_urls(Error404)
    print "Error 404 pages urls have been adapted"
    #write_responses("lenght_error404_links_parsed", Error404, error404_counter)
    Http_error=adapt_urls(Http_error)
    print "Http error pages urls have been adapted"
    #write_responses("Http_error_links_parsed", Http_error, httperror_counter)
#     Timeout_error=adapt_urls(Timeout_error)
#     print "Timeout pages urls have been adapted"
#     Exception_error=adapt_urls(Exception_error)
#     print "Exception pages urls have been adapted"
    print "------------------------"
    
    length_empty_links, lenght_error404_links, length_httperror=reset_counters()
    
    if FIX:
        print "------------------------"
        with Timer('calculation-web-empty'):
            for i in range(length_empty_links):
                parse(Empty[2][i], False, "website", "empty")
                empty_counter=empty_counter+1
        write_responses("empty_links_compared", Empty, empty_counter)
        with Timer('calculation-web-error404'):   
            for i in range(lenght_error404_links):
                parse(Error404[2][i], False, "website", "error404")
                error404_counter=error404_counter+1
        write_responses("error404_links_compared", Error404, error404_counter)
        with Timer('calculation-web-httperror'):
            for i in range(length_httperror):
                parse(Http_error[2][i], False, "website", "httperror")
                httperror_counter=httperror_counter+1
        write_responses("Http_error_links_compared", Http_error, httperror_counter)
        print empty_counter, error404_counter, httperror_counter#, timeout_counter, exception_counter
        print "------------------------"
    else:
        Empty, empty_counter=read_files("empty_links_compared", Empty)
        Error404, error404_counter=read_files("error404_links_compared", Error404)
        Http_error, httperror_counter=read_files("Http_error_links_compared", Http_error)
    print "------------pre fixing------------"
    print "Empty pages: "+str(empty_counter)
    print "Error 404 pages: "+str(error404_counter)
    print "Http error pages: "+str(httperror_counter)
    print "Fixed pages: "+str(fixed_counter)
    print "------------------------"
    length_empty_links, lenght_error404_links, length_httperror=reset_counters()
    
    print "------------fixing with website------------"
    Empty, empty_counter=add_fixed(Empty, "website")
    write_responses("empty_links_after_firstfix", Empty, empty_counter)
    Error404, error404_counter=add_fixed(Error404, "website")
    write_responses("error404_links_after_firstfix", Error404, error404_counter)
    Http_error, httperror_counter=add_fixed(Http_error, "website")
    write_responses("Http_error_links_after_firstfix", Http_error, httperror_counter)
    
#     Timeout_error, timeout_counter=add_fixed(Timeout_error)
#     Exception_error, exception_counter=add_fixed(Exception_error)
    f = open("files/fixed.csv", "w")
    f.write("original|fixed"+"\n")
    f.close()
    write_responses("fixed", Fixed, fixed_counter)
    
    print "-----------after website fixing-------------"
    print "Empty pages: "+str(empty_counter)
    print "Error 404 pages: "+str(error404_counter)
    print "Http error pages: "+str(httperror_counter)
    print "Fixed pages: "+str(fixed_counter)
    print "------------------------"
    length_empty_links, lenght_error404_links, length_httperror=reset_counters()
    
    print "------------fixing with web.archive------------"
    Empty, empty_counter=crawl_webarchive(Empty)
    Empty, empty_counter=add_fixed(Empty, "archive")
    write_responses("empty_links_after_secondfix", Empty, empty_counter)
    Error404, error404_counter=crawl_webarchive(Error404)
    Error404, error404_counter=add_fixed(Error404, "archive")
    write_responses("error404_links_after_secondfix", Error404, error404_counter)
    Http_error, httperror_counter=crawl_webarchive(Http_error)
    Http_error, httperror_counter=add_fixed(Http_error, "archive")
    write_responses("Http_error_links_after_secondfix", Http_error, httperror_counter)
    write_responses("fixed", Fixed, fixed_counter)
    
    print "-----------after web.archive fixing-------------"
    print "Empty pages: "+str(empty_counter)
    print "Error 404 pages: "+str(error404_counter)
    print "Http error pages: "+str(httperror_counter)
    print "Fixed pages: "+str(fixed_counter)
    print "------------------------"

    