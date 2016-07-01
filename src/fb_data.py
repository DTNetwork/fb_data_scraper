import facebook, requests, json,sys, time, datetime, os
from models import db, Comments, Posts
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import threading, re
requests.packages.urllib3.disable_warnings()

from flask import Flask
app = Flask(__name__)
app.config.from_object('settings.Config')
db.init_app(app)
graph = facebook.GraphAPI(app.config['FB_ACCESS_TOKEN'])


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
                          c_time = datetime.datetime.strptime(comment.get('created_time'),'%Y-%m-%dT%H:%M:%S+0000')
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
                p_time = datetime.datetime.strptime(post.get('created_time'),'%Y-%m-%dT%H:%M:%S+0000')
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
    save_comments()      

if __name__=="__main__":
    with app.app_context():
        # pass
        save_posts()