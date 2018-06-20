# -*- coding: utf-8 -*-

import facebook, requests, json,sys, time, os
import datetime as datetimeModule
from models import db, Comments, Posts
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import threading, re
requests.packages.urllib3.disable_warnings()

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
app = Flask(__name__)
app.config.from_object('settings.Config')
db.init_app(app)
graph = facebook.GraphAPI(app.config['FB_ACCESS_TOKEN'])


# For scraping
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from datetime import datetime, date, timedelta



#Takes the first 25 posts for the page as input and uses the 'next' link given by FB along with the 25 posts to get next 25 posts and so on until there is no link to 'next'
def get_posts(posts):
  post_list = []
  while posts.get('paging').get('next'):
    for post in posts['data']:
      post_list.append(post)
    return post_list
    temp_posts = requests.get(posts['paging']['next']).json()
    if temp_posts.get('paging'):
      posts = temp_posts
    else:
      break
  for post in posts['data']:
    post_list.append(post)
  return post_list

#Takes the first set of comments for the post as input and uses the 'next' link given by FB in the first set of comments to get next set of comments and so on until there is no link to 'next'
def get_comments(comments):
  comments_list = []
  if comments==None and comments.get('data'):
    return comments['data']
  while comments.get('paging')!=None and comments.get('paging').get('next'):
    for comment in comments['data']:
      comments_list.append(comment)
    temp_comments = requests.get(comments['paging']['next']+"&limit=100").json()
    if temp_comments.get('paging'):
      comments = temp_comments
    else:
      break
  for comment in comments['data']:
    comments_list.append(comment)
  return comments_list

def check_null(post, val):
    if not(post.get(val)):
        return ""
    if type(post.get(val))!="str":
        return post.get(val)
    else:
        return post.get(val)

def save_comments():
    for elem in app.config['PAGE_LIST']:
        #Fetch all the post_id for the posts belonging to current page from PAGE_LIST
        post_list = db.session.query(Posts.post_id).filter(Posts.candidate==elem.lower()).all()
        for idx, pst in enumerate(post_list):
            post = pst[0] #DB returns a list of tuple with post_id as the only element in the tuple, so we use index=0 to get the first and the only item from the tuple
            #Check if there is any comment in database which has this post_id, if yes that means the comments for this post has already been saved to the db and we can skip to the next one
            if db.session.query(Comments).filter(Comments.post_id==post).count()<1 :
                try:
                    #Get comments from FB API using the post ID
                    comments = graph.get_connections(post, 'comments')
                    #Send the First set of comments to the get_comments() function to get the rest of the comments from the API.
                    print "Getting comments for Post: %s and page: %s " % (post, elem)
                    comment_list = get_comments(comments)
                    print "Number of comments for Post: %s: %s" % (post, len(comment_list))
                    if len(comment_list)!=50:
                      for comment in comment_list:
                          c_time = datetimeModule.datetime.strptime(comment.get('created_time'),'%Y-%m-%dT%H:%M:%S+0000')
                          db.session.add(Comments(post, c_time, elem.lower(), check_null(comment, "message"), check_null(comment, "id"), \
                            check_null(comment, "like_count") if check_null(comment, "like_count")!='' else 0, comment['from']['id'], comment['from']['name']))
                      try:
                          db.session.commit()
                          print "added data for post: " + str(idx) 
                      except Exception as ee:
                          print ee
                          exc_type, exc_obj, exc_tb = sys.exc_info()
                          fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                          print(exc_type, fname, exc_tb.tb_lineno)
                          db.session.rollback()
                          db.session.flush()
                          print "rollback happened"
                except Exception as e:
                    if 'Unsupported get request' in str(e) or 'name' in str(e) or 'JSON object' in str(e):
                      pass
                    else:
                      print elem + ": error: "+str(e) + ": index: " +str(idx)
                      exc_type, exc_obj, exc_tb = sys.exc_info()
                      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                      print(exc_type, fname, exc_tb.tb_lineno)
                      raise SystemExit(0)

            else:
                print "already done: "+ str(idx)

# scraping
def scroll_to_end_get_all_posts(driver, inputURL):

    TIME_TO_LOAD_PAGES = app.config["TIME_TO_LOAD_PAGES"]

    driver.get(inputURL)
    time.sleep(TIME_TO_LOAD_PAGES)
    driver.find_element_by_link_text('Discussion').click()
    time.sleep(TIME_TO_LOAD_PAGES)

    print("Scrolling to end of page: ", inputURL)
    print("This might take a while. Just relax and try taking few deep breaths while your computer is at work!")

    
    last_height = driver.execute_script("return document.body.scrollHeight")

    scrolledN = 0
    # while True:
    while scrolledN < 3:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(TIME_TO_LOAD_PAGES)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scrolledN += 1
        print("Scrolled number of times: ", scrolledN)
    print("Done with scrolling to end of page!")

    # returning list ids for the "_4-u2 mbm _4mrt _5jmm _5pat _5v3q _4-u8" class
    return [aPost.get_attribute("id") for aPost in driver.find_elements_by_xpath('//div[contains(@class, "_4-u2") and contains(@class, "mbm") and contains(@class, "_4mrt") and contains(@class, "_5jmm") and contains(@class, "_5pat") and contains(@class, "_5v3q") and contains(@class, "_4-u8")]')]

# scraping
class Post():
    """Class to contain information about a post"""

    def __init__(self):
        self.post_id = "scrapped_SoNoID"
        self.post_date = ""
        self.post_msg = ""
        self.candidate = ""
        self.no_comments = 0
        self.no_likes = 0
        self.no_shares = 0
        self.post_type = "status"
        self.poster_name = ""
        

    def toDict(self):
        return self.__dict__.copy()

    def fromDict(self, d):
        self.__dict__ = d.copy()

    def from_json(self, j):
        self.fromDict(json.loads(j))

    def from_json_file(self, f):
        self.fromDict(json.loads(open(f, "rt").read()))

    def to_json(self):
        return json.dumps(self.toDict())

    def __str__(self):
        s = self.post_id + ": " + \
        str(self.post_date) + ": " + \
        self.post_msg + ": " + \
        self.candidate + ": " + \
        str(self.no_comments) + ": " + \
        str(self.no_likes) + ": " + \
        str(self.no_shares) + ": " + \
        self.post_type
        
        s += "\n"
        return s

    def __repr__(self):
        return self.__str__()

# scraping
class parsePost():
    def __init__(self, driver, anID, ele):
        self.driver = driver
        self.anID = anID
        self.ele = ele
    
    def get_post_id(self, thisPostDate):
        partZero = "".join("".join(self.anID.split("_")).split(":"))
        
        parts = thisPostDate.split(" ")
        partOne = "".join(parts[0].split("-"))
        partTwo = "".join(parts[1].split(":"))
        
        return partZero + partOne + partTwo

    def get_comment_id(self, post_id, comment_date):
        partZero = post_id[:len(post_id)//2]

        parts = comment_date.split(" ")
        partOne = "".join(parts[0].split("-"))
        partTwo = "".join(parts[1].split(":"))

        return partZero + partOne + partTwo

    def get_post_type(self):
        processedPost = self.driver.find_element_by_id(self.anID).find_element_by_class_name("fwn").text
        
        parsedPostType = processedPost.split(" ")[-1][:-1]
        if parsedPostType in ["link", "video", "post", "event", "Page", "recommendations"]:
            return parsedPostType
        return 'status'
    
    def get_poster_name (self):
        return self.driver.find_element_by_id(self.anID).find_element_by_class_name("fwb").text
        
    def get_post_date (self, processedPost = None):
        if not processedPost:
            processedPost = self.driver.find_element_by_id(self.anID).find_element_by_class_name("fsm").text
        
        months = ["January", "February", "March", "April", "May", "June", 
             "July", "August", "September", "October", "November", "December"]
      
    #     To handle conditions like 'June 2 at 6:58am  Rome, Italy'
        middleDot = u'·'
        middleDot = middleDot.encode('utf-8')
        if middleDot in processedPost.encode('utf-8'):
            processedPost = processedPost.encode('utf-8').split(middleDot)[0].strip()

        parsedTimeSplit = processedPost.split(" ")

        # Yesterday at 4:14am
        if 'yesterday' in processedPost.lower():
            try:
                processedPost = processedPost.replace("Yesterday", (date.today() - timedelta(1)).__str__())
                timetup = time.strptime(processedPost, '%Y-%m-%d at %I:%M%p')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: Yesterday at 4:14am")

        # 7 hrs
        elif "hrs" in processedPost.lower():
            try:
                n = 7
                timetup = time.strptime((datetime.today() - timedelta(hours=n)).__str__(), '%Y-%m-%d %H:%M:%S.%f')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: 7 hrs")

        # April 18 2018 at 3:52am
        elif "at" in processedPost and parsedTimeSplit[0] in months and 5 == len(parsedTimeSplit):
            try:
                timetup = time.strptime(processedPost, '%B %d %Y at %I:%M%p')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: April 18 2018 at 3:52am")

        # June 11 at 11:02pm
        elif "at" in processedPost and parsedTimeSplit[0] in months:
            try:
                today = datetime.today()
                y = str(today.year) + " "

                # adding currect year
                index = processedPost.find('at')
                processedPost = processedPost[:index] + y + processedPost[index:]

                timetup = time.strptime(processedPost, '%B %d %Y at %I:%M%p')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: June 11 at 11:02pm")

        # June 11
        elif 2 == len(parsedTimeSplit) and parsedTimeSplit[0] in months:
            try:
                today = datetime.today()
                y = str(today.year)

                # Adding current Year
                processedPost = processedPost + " " + y 

                timetup = time.strptime(processedPost,'%B %d %Y')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: June 11")

        # July 22, 2017
        else:
            try:
                timetup = time.strptime(processedPost, '%B %d, %Y')
                return time.strftime('%Y-%m-%d %H:%M:%S', timetup)
            except ValueError:
                print("Expecting a format similar to: July 22, 2017")
                
    def get_post_message (self):
        content = self.driver.find_element_by_id(self.anID).find_element_by_class_name("userContent").text
        hasSharedContent = ""
        try:
          hasSharedContent = self.driver.find_element_by_id(self.anID).find_element_by_class_name("_6m3").text
        except NoSuchElementException:
          pass

        return content + hasSharedContent
    
    def get_no_of_shares (self):
        processedPost = ""
        try:
            processedPost = self.driver.find_element_by_id(self.anID).find_element_by_class_name("UFIShareRow").text
        except NoSuchElementException:
            return 0

        noOfShares = 0
        if processedPost and re.search( 'Share*', processedPost) and len(processedPost.split(" ")) == 2:
            noOfShares =  int(processedPost.split(" ")[0])
        return noOfShares
            
    def get_no_of_likes (self):
        try:
            processedPost = self.driver.find_element_by_id(self.anID).find_element_by_class_name("UFILikeSentence").text
        except NoSuchElementException:
            return 0

        noOfLikes = 0
        if re.search( 'like*', processedPost):
            commas = processedPost.count(',')
            ands =  processedPost.count('and')
            otherLikes = re.findall(r'\d+', processedPost)
            otherLikes = int(otherLikes[0]) if len(otherLikes) else 0
            if 1 == commas and 1 == ands and 0 == otherLikes:
                noOfLikes =  3
            elif 1 == commas and 1 == ands and otherLikes:
                noOfLikes =  2 + otherLikes
            elif 0 == commas and 1 == ands:
                noOfLikes =  2
            elif 0 == commas and 0 == ands:
                noOfLikes =  1
            elif 2 == commas and 1 == ands and otherLikes:
                noOfLikes =  3 + otherLikes
        # If you are logged in and scrapping the groups page, likes will be consolidated and look like this "4 \n4"
        # So using regular expression
        elif re.findall(r'\d+', processedPost):
            return int(re.findall(r'\d+', processedPost)[0])

        return noOfLikes

    def save_scraped_comments (self):

        import pdb; pdb.set_trace()

        post_id = self.get_post_id(self.get_post_date())
        candidate = self.ele
        noOfComments = len(self.driver.find_element_by_id(self.anID).find_elements_by_class_name("UFIComment"))

        for n in range(noOfComments):
            thisComment = self.driver.find_element_by_id(self.anID).find_elements_by_class_name("UFIComment")[n].find_element_by_class_name("UFICommentBody").text
            commenter_name = self.driver.find_element_by_id(self.anID).find_elements_by_class_name("UFIComment")[n].find_element_by_class_name("UFICommentActorName").text
            comment_date = self.driver.find_element_by_id(self.anID).find_elements_by_class_name("UFIComment")[n].find_element_by_class_name("UFISutroCommentTimestamp").get_attribute("title")
            comment_date = " ".join(eachPart.strip() for eachPart in comment_date.split(",")[1:])
            comment_date = self.get_post_date(comment_date)
            try: 
              like_count = self.driver.find_element_by_id(self.anID).find_element_by_class_name("_10lo").text
              like_count = int(like_count) if like_count else 0
            except NoSuchElementException:
              pass
            commenter_id = "scrapped_SoNoID"
            comment_id = self.get_comment_id(post_id, comment_date)

            db.session.add(Comments(post_id, comment_date, candidate, thisComment, comment_id, \
              like_count, commenter_id, commenter_name))
            try:
                db.session.commit() 
            except Exception as ee:
                pass
        return noOfComments

    def get_no_of_comments (self):

        LOAD_COMMENTS_WAIT_PERIOD = 3

        print("IN GET COMMENTS: ID - ", self.anID)
        if "mall_post_845632185635942:6:0" == self.anID:
            import pdb; pdb.set_trace()

        try: 
          # self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("more comments").click()
          element = self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("more comments")
          self.driver.execute_script("arguments[0].click();", element)
          time.sleep(LOAD_COMMENTS_WAIT_PERIOD)
          # self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("View more replies").click()
          # time.sleep(LOAD_COMMENTS_WAIT_PERIOD)
          # self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("more comments").click()
          # time.sleep(LOAD_COMMENTS_WAIT_PERIOD)
          # self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("View more replies").click()
          # time.sleep(LOAD_COMMENTS_WAIT_PERIOD)
        except NoSuchElementException:
          pass

        # result = MAX_TRYS
        # while result > 0:
        #   result = result - 1
        #   try: 
        #     self.driver.find_element_by_id(self.anID).find_element_by_partial_link_text("replied").click()
        #     time.sleep(LOAD_COMMENTS_WAIT_PERIOD)
        #   except NoSuchElementException:
        #     pass

        try:
          self.driver.find_element_by_id(self.anID).find_element_by_class_name("UFIComment").find_element_by_class_name("UFICommentBody")
        except NoSuchElementException:
            return 0

        noOfComments = self.save_scraped_comments()

        # return len(self.driver.find_element_by_id(self.anID).find_elements_by_class_name("UFIComment"))
        return noOfComments

    
def save_scraped_posts():

  TIME_TO_LOAD_PAGES = app.config["TIME_TO_LOAD_PAGES"]

  # Initializing Selenium ChromeDriver
  chrome_options = Options()
  chrome_options.add_argument("--headless")
  chrome_options.add_argument("--window-size=1920x1080")
  chrome_driver = os.getcwd() + "/chromedriver"
  driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

  # Opening facebook
  driver.get("https://www.facebook.com")
  time.sleep(TIME_TO_LOAD_PAGES)

  # logging in. You can enter these usernames and passwords in settings.py
  fb_username = app.config['FB_USERNAME']
  fb_password = app.config['FB_PASSWORD']
  print("Logging in with username: ", fb_username, " and password: ", fb_password)
  driver.find_element_by_name("email").send_keys(fb_username)
  driver.find_element_by_name("pass").send_keys(fb_password)
  driver.find_element_by_id("loginbutton").click()
  time.sleep(TIME_TO_LOAD_PAGES)

  # Iterating through each page mentioned in the list.
  for ele in app.config["GROUP_PAGE_LIST"]:
    url = "https://www.facebook.com/groups/" + ele + "/"
    allPostIDs = scroll_to_end_get_all_posts(driver, url)

    print()
    print("Parsing. Extracting relevant data. Commiting to DB. For ", ele)
    totalNumberOfPosts = len(allPostIDs)
    for n, ID in enumerate(allPostIDs):
      print(totalNumberOfPosts - n + 1, " posts yet to scrap!")
      bot = parsePost(driver, ID, ele.lower())
      thisPostDetails = Post()

      thisPostDetails.candidate = ele.lower() # url.split("/")[-2]
      thisPostDetails.post_type = bot.get_post_type()
      thisPostDetails.poster_name = bot.get_poster_name()
      thisPostDetails.post_date = bot.get_post_date()
      thisPostDetails.post_msg = bot.get_post_message()
      thisPostDetails.no_shares = bot.get_no_of_shares()
      thisPostDetails.no_likes = bot.get_no_of_likes()
      thisPostDetails.no_comments = bot.get_no_of_comments()
      thisPostDetails.post_id = bot.get_post_id(thisPostDetails.post_date)

      # print(thisPostDetails.__str__())

      db.session.add(Posts(thisPostDetails.post_id, thisPostDetails.post_date, thisPostDetails.candidate, \
        thisPostDetails.post_msg, thisPostDetails.no_comments, thisPostDetails.no_likes, thisPostDetails.no_shares, thisPostDetails.post_type))
      db.session.commit()

#GET posts from facebook for all the pages in PAGE_LIST which is defined as a list in settings.py
def save_posts():
    for ele in app.config['PAGE_LIST']:
        #Query FB API to get first 25 posts for the current page
        posts = graph.get_connections(ele, 'posts', limit=25, fields='likes.summary(true),comments.summary(true),name,message,type,id,created_time,shares')
        print "Getting posts for: %s" % (ele,)
        #Send the First 25 posts to the get_posts() function to get the rest of the posts from the API.
        post_list = get_posts(posts)
        print "Number of Posts for %s: %s" % (ele, len(post_list))
        for idx, post in enumerate(post_list):
            try:
                p_time = datetimeModule.datetime.strptime(post.get('created_time'),'%Y-%m-%dT%H:%M:%S+0000')
                
                #Add the post to the Database Session
                db.session.add(Posts(check_null(post, "id"), p_time, ele.lower(), check_null(post, "message"), \
                   str(post.get("comments").get("summary").get("total_count")) if post.get("comments") else str(0),  \
                   str(post.get("likes").get("summary").get("total_count")) if post.get("likes") else str(0),\
                   str(post.get("shares").get("count")) if post.get("shares") else str(0), check_null(post, "type")))
                #Commit the session to complete the DB Transaction
                db.session.commit()
            except Exception as e:
                if 'ADD_YOUR_OWN_KEYWORD_TO_SKIP_POST_WITH_ERRORS_TO_CONTINUE_TO_NEXT_POST' in str(e):
                    pass
                else:
                    print ele + ": error: "+str(e) + ": index: " +str(idx)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)
                    raise SystemExit(0) 

    # As Facebook Graph API can only be used by 'App review', we are scrapping instead as we need data from very few pages.
    save_scraped_posts()
    save_comments()      

if __name__=="__main__":
    with app.app_context():
        # pass
        save_posts()