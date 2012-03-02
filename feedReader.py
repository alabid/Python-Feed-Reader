"""
feedReader.py
By Daniel Alabi and Michael Domingues

A basic RSS feed reader.
Usage: python feedReader.py feeds [options]

Requires the feedparser module.

'feeds' is a mandatory text file containing a list of feed URLs,
and the options are as follows:

--date                 Display the story links in order of date posted, from
                       newest to oldest (not grouped by feed).

--alpha                Display the story links ordered by feed, with the feeds
                       ordered alphabetically.

--n NUM                Display the latest NUM story links in each feed, where
                       NUM is an integer value.

--since DATE           Display the story links in each feed published on or
                       after the specified date. DATE must be in the form
                       YYYY-MM-DD.

--title REGEX          Display the stories whose titles match the regular
                       expression REGEX.

--description {on|off} Display the description associated with a story.
                       Defaults to off.

--newest               Display only the stories that have been posted or
                       updated since the last time this program was run.

By default, this program displays items grouped by feed, in the order
that the feeds were listed in the input file.

Note that multiple command line options can be triggered; they will be
processed and displayed sequentially. For example, if you were to run:
    'python feedReader.py feedsList.txt --date --alpha'
the program would first present the date view, followed by the alpha view.

For the purposes of this program, our dummy time is 1000-01-01 00:00:00.

For more information, see README.txt
"""

import feedparser

class Controller(object):
    """
    The Controller class is the center of execution of commands and views.
    """
    def __init__(self, options, args):
        # options is a 'Values' object, the
        # output from the optparser.
        self.options = options
        self.args = args
        self.feeds = []
        self.lastSeenTime = None

        self.setLastSeenTime()
        # Begin execution of the program
        self.run()
        
    def setLastSeenTime(self):
        """
        Sets the instance variable self.lastSeenTime to the last time
        this program was run. If this is the first run of the program or
        the data file lastSeen.txt does not exist / was deleted, sets
        self.lastSeenTime to our standard dummy time.
        """
        import glob
        from time import gmtime, strftime

        dateFile = "lastSeen.txt"
        if not glob.glob(dateFile):
            self.lastSeenTime = PubTime((1000, 1, 1, 0, 0, 0))
            lastSeenFile = open(dateFile, 'w')
            timeString = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            lastSeenFile.write(timeString)
            lastSeenFile.close()
        else:
            # Read from the dateFile.
            lastSeenFile = open(dateFile, 'r')
            timeString = lastSeenFile.read()
            self.lastSeenTime = self.timeStringToPubTime(timeString)
            lastSeenFile.close()
            # Re-open and then write the current time to the dateFile.
            lastSeenFile = open(dateFile, 'w')
            timeString = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            lastSeenFile.write(timeString)
            lastSeenFile.close()

    def getFeedsFromFile(self, feedFile):
        """
        Given a file containing a list of URLs (one per line),
        returns a list of the URLs.
        """
        feedList = []
        try:
            with open(feedFile, "r") as openFile:
                possibleFeeds = openFile.readlines()
            # The following list comprehension makes possibleFeeds a list
            # of links stripped of newlines.
            possibleFeeds = [link.strip() for link in possibleFeeds if \
                             link != '\n']
            for link in possibleFeeds:
                feedList.append(self.appendHTTP(link))
            return feedList
        except:
            errorMessage = "The file " + feedFile + \
                           " does not exist or is not valid."
            raise FeedReaderError(errorMessage)

    def makeFeed(self, parserData):
        """
        Given the output of feedparser.parse(), validate that
        we do have a feed, and return a Feed object. If the feed is invalid,
        returns a feed object with the title 'ERROR'.
        """
        # Import classes for error type checking.
        from urllib2 import URLError
        from xml.sax._exceptions import SAXParseException as SynErr

        # parserData.bozo will equal 1 if the feed is malformed, or
        # 0 if it is well formed.
        if parserData.bozo == 1:
            if isinstance(parserData.bozo_exception, URLError) or \
                isinstance(parserData.bozo_exception, SynErr):
                return Feed("ERROR", "")
        # Make the feed object.
        title = ""
        pubDate = ""
        hasTitle = parserData.feed.has_key("title")
        hasPubDate = parserData.feed.has_key("updated_parsed")
        if hasPubDate:
            pubDate = parserData.feed.updated_parsed
        if hasTitle:
            title = parserData.feed.title
        if hasPubDate or hasTitle:
            feed = Feed(title, pubDate)
            if parserData.has_key("entries"):
                for entry in parserData.entries:
                    feed.addItem(Item(entry))
            return feed
        else:
            return Feed("ERROR", "")

    ############### Accessors and Mutators ###############

    def getFeeds(self):
        """
        Returns a copy of the internal feeds list.
        """
        return self.feeds[:]
        
    def addFeed(self, feedObject):
        """
        Appends the given Feed object to the internal list
        of feeds.
        """
        self.feeds.append(feedObject)

    ############### Helper Methods ###############

    def appendHTTP(self, url):
        """
        Appends http:// to the beginning of a potential url
        if it is not already present and returns the url.
        """
        import re
        
        if not re.match("^http[s]?://(?!/)", url):
            url = "http://" + url
        return url

    def timeStringToPubTime(self, timeString):
        """
        This method takes in a timeString in format
        YYYY-MM-DD HH:MM:SS and converts it to a PubTime object which it
        returns.
        """
        date, time = timeString.split(' ')
        year, month, day = date.split('-')
        hour, minute, sec = time.split(':')
        timeArray = [year, month, day, hour, minute, sec]
        timeTuple = tuple(map(int, timeArray))
        return PubTime(timeTuple)

    def setFeedDescriptionFlag(self, feed):
        if self.options.description.lower() == "on":
            feed.descOn = True

    def setItemDescriptionFlag(self, item):
        if self.options.description.lower() == "on":
            item.descOn = True
            
    ############### Views ###############
            
    def defaultView(self):
        """
        Displays feeds in the same order as they are listed in the
        input file.
        """
        for feed in self.getFeeds():
            self.setFeedDescriptionFlag(feed)
            feed.printFeed()

    def dateView(self):
        """
        Displays the items in order by date, from newest to oldest.
        Entries with no date are not displayed.
        """
        printList = []
        for feed in self.getFeeds():
            for entry in feed.getItems():
                printList.append(entry)
        printList.sort(key=lambda entry: entry.getPubDate())
        printList.reverse()
        for entry in printList:
            self.setItemDescriptionFlag(entry)
            if entry.getPubDate() != PubTime((1000, 1, 1, 0, 0, 0)):
                print entry

    def alphaView(self):
        """
        Displays the feeds in alphabetical order.
        """
        feedsList = self.getFeeds()
        feedsList.sort(key=lambda feed: feed.getTitle())
        for feed in feedsList:
            self.setFeedDescriptionFlag(feed)
            feed.printFeed()

    def numView(self, n):
        """
        Displays the latest n items in each feed.
        """
        for feed in self.getFeeds():
            self.setFeedDescriptionFlag(feed)
            feed.printFeed(numItems=n)

    def sinceView(self, withLastSeen=False):
        """
        Displays the items published or updated since date specified at
        the command line. If withLastSeen == True, displays the items
        published or updated since the last time this program was run.
        """
        if not withLastSeen:
            sinceDate = self.options.since.split("-")
            year = int(sinceDate[0])
            month = int(sinceDate[1])
            day = int(sinceDate[2])
            date = PubTime((year, month, day, 0, 0, 0))
        else:
            date = self.lastSeenTime
        for feed in self.getFeeds():
            self.setFeedDescriptionFlag(feed)
            feed.printFeed(sinceDate=date)

    def titleView(self):
        """
        Displays the items whose titles are matched by the regular
        expression specified at the command line.
        """
        import re
        
        printList = []
        for feed in self.getFeeds():
            for entry in feed.getItems():
                if re.search(self.options.title, entry.getTitle()):
                    printList.append(entry)
        for entry in printList:
            self.setItemDescriptionFlag(entry)
            print entry

    def newestView(self):
        """
        Wrapper for sinceView. Displays items that have been updated or
        published since the last time the program was run.
        """
        self.sinceView(withLastSeen=True)

    ############### Execution ###############

    def run(self):
        """
        Sets up the program, and sequentially executes the views specified
        at the command line.
        """
        # Process the input. self.args[0] is the input file.
        feedList = self.getFeedsFromFile(self.args[0])
        for feed in feedList:
            feedObject = self.makeFeed(feedparser.parse(feed))
            if feedObject.getTitle() != "ERROR":
                self.addFeed(feedObject)
        
        # Set up the views        
        optionsAreTriggered = (self.options.date or self.options.alpha or \
                               (self.options.n > -1) or self.options.since or \
                               self.options.title or self.options.newest)
        # Run the view(s)
        if optionsAreTriggered:
            if self.options.date:
                print "\n###### DATE VIEW ######\n"
                self.dateView()
            if self.options.alpha:
                print "\n###### ALPHA VIEW ######\n"
                self.alphaView()
            if (self.options.n > -1):
                print "\n###### NUM VIEW ######\n"
                self.numView(self.options.n)
            if self.options.since:
                print "\n###### SINCE VIEW ######\n"
                self.sinceView()
            if self.options.title:
                print "\n###### TITLE VIEW ######\n"
                self.titleView()
            if self.options.newest:
                print "\n###### NEWEST VIEW ######\n"
                self.newestView()
        else:
            self.defaultView()


class Feed(object):
    """
    A Feed stores title, publication date (pubDate), and the stories associated 
    with the feed it comes from.
    """    
    def __init__(self, feedTitle, feedPubDate):
        # Some of this data might not exist; specifically feedPubDate.
        self.title = str(feedTitle)
        self.pubDate = feedPubDate
        self.items = []
        
        # self.descOn is false by default. It is a flag set by the Controller 
        # that specifies if the user wants to display the description associated
        # with a story link.
        self.descOn = False        

    def getTitle(self):
        return self.title

    def getPubDate(self):
        return self.pubDate

    def getItems(self):
        return self.items

    def addItem(self, item):
        self.items.append(item)

    def printFeed(self, numItems=-1, sinceDate=-1):
        """
        Prints the feed and its contained items according to the options
        specified.
        """
        # If numItems is not specified, print all stories.
        if numItems == -1:
            numItems = len(self.items)
        # If sinceDate is not specified, print all stories.
        if not isinstance(sinceDate, PubTime):
            sinceDate = PubTime((1000, 1, 1, 0, 0, 0))
        string = "Feed: " + self.getTitle() \
                 + "\n===============================\n"
        for entry in self.getItems()[0:numItems]:
            if self.descOn:
                entry.descOn = True
            if entry.getPubDate() >= sinceDate:
                string += str(entry) + '\n'
        print string

        
class Item(object):
    """
    A single story formed from an feedparser entry. Instance variables are
    initialized to empty strings, and are then populated.
    """
    def __init__(self, entry):
        # Some of this data might not exist; specifically itemPubDate
        # self.content will be a unicode string.
        self.title = ""
        self.url = ""
        self.pubDate = PubTime((1000, 1, 1, 0, 0, 0)) # Dummy time
        self.content = u"" # A unicode string
        self.descOn = False
        
        self.populate(entry)

    def getTitle(self):
        return self.title

    def getURL(self):
        return self.url

    def getPubDate(self):
        return self.pubDate

    def getContent(self):
        return self.content

    def stripTags(self, summary):
        """A helper method to stript html tags and entities from a string."""
        import re
        
        return re.sub("</?[\w]*.*?/?>|&#?\w+;","", summary)        

    def populate(self, entry):
        """
        This populates the Item object with properties extracted from
        the entry parameter.
        """
        if entry.has_key("title"):
            titleString = entry.title.encode('UTF-8')
            self.title = self.stripTags(titleString)
        if entry.has_key('link'):
            self.url = str(entry.link)
        if entry.has_key("summary"):
            self.content = self.stripTags(entry.summary)
        # If published_parsed exists, use it to set self.pubDate. Otherwise, use
        # updated_parsed.
        if entry.has_key("published_parsed"):
            self.pubDate = PubTime(entry.published_parsed)
        elif entry.has_key("updated_parsed"):
            self.pubDate = PubTime(entry.updated_parsed)            

    def __str__(self):
        string = self.getTitle() + "\n----------------------"
        if str(self.getPubDate().getYear()) != "1000":
            # If the entry has a publication date, add it to the string.
            string += "\nPublished: " + str(self.getPubDate())
        if str(self.getURL()) != "":
            # If the entry has a URL, add it to the string.
            string += "\nLink: " + self.getURL()
        if self.descOn:
            string += "\nDescription: " + self.content.encode('UTF-8')
        string += "\n"
        return string

   
class PubTime(object):
    """
    A PubTime is an object that keeps time in a format easily used by the
    program.
    """
    def __init__(self, time_tuple):
        import datetime

        self.year = time_tuple[0]
        self.month = time_tuple[1]
        self.day =  time_tuple[2]
        self.hour =  time_tuple[3]
        self.min =  time_tuple[4]
        self.sec =  time_tuple[5]
        
        self.dateTime = datetime.datetime(*time_tuple[0:6])

    def getYear(self):
        return self.year

    def getMonth(self):
        return self.month

    def getDay(self):
        return self.day

    def getHour(self):
        return self.hour

    def getMin(self):
        return self.min

    def getSec(self):
        return self.sec

    def __cmp__(self, other):
        """
        Compares two PubTime objects to each other. Returns -1 if this PubTime
        is earlier than the other PubTime object, returns 0 if they are equal, 
        and 1 if this object is later than the other object.
        """
        if self.dateTime.__lt__(other.dateTime):
            return -1
        elif self.dateTime.__gt__(other.dateTime):
            return 1
        else:
            return 0

    def __str__(self):
        """Returns the time in YYYY-MM-DD HH:MM:SS format."""
        return self.dateTime.isoformat(' ')
        

class FeedReaderError(Exception):
    """
    A subclass of the built-in Python Exception class, to throw
    errors and quit.
    """
    def __init__(self, errorMessage):
        self.errorMessage = errorMessage

    def __str__(self):
        return repr(self.errorMessage)


############### Helper Functions ###############

def processCmdLineArgs():
    from optparse import OptionParser
    
    parser = OptionParser()
    parser.add_option("--date", action="store_true")
    parser.add_option("--alpha", action="store_true")
    parser.add_option("-n", type="int")
    parser.add_option("--since", type="string")
    parser.add_option("--title", type="string")
    parser.add_option("--description", type="string", default="off")
    parser.add_option("--newest", action="store_true")
    return parser.parse_args()

def validateCmdLineArgs(options, args):
    """
    Validates commandline options and arguments; raises FeedReaderError
    as needed.
    """
    descriptionFlag = options.description.lower()
    # Check for missing / extra parameters
    if len(args) != 1:
        raise FeedReaderError("Check commandline parameters.")
    # Check for incorrectly used options
    elif not isDateValid(options.since):
        raise FeedReaderError("Date must be in this format: 'YYYY-MM-DD'")
    elif (descriptionFlag != "on") and (descriptionFlag != "off"):
        raise FeedReaderError("--description must be either 'on' or 'off'.")

def isDateValid(date):
    """
    Returns True if the given date is in YYYY-MM-DD form, else returns
    False.
    """
    
    import re

    datePt = "^\d{4}-([0][1-9]|[1][0-2])-([0][1-9]|[1][0-9]|[2][0-9]|[3][0-1])$"
    if (not date) or re.match(datePt, date):
        return True
    return False

############### Execution ###############

def main():
    try:
        options, args = processCmdLineArgs()
        validateCmdLineArgs(options, args)
        feedReader = Controller(options, args)
    except FeedReaderError as feedError:
        print "FeedReaderError:", feedError

if __name__ == "__main__":
    main()
