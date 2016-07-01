from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Index
db = SQLAlchemy()


class Posts(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    post_id = db.Column(db.String(), index=True)
    post_date =  db.Column(db.DateTime())
    candidate = db.Column(db.String(), index=True)
    post_msg = db.Column(db.String())
    no_comment = db.Column(db.Integer())
    no_likes = db.Column(db.Integer())
    no_shares = db.Column(db.Integer())
    post_type = db.Column(db.String(), index=True)

    def __init__(self, post_id, post_date, candidate, post_msg, no_comment, no_likes, no_shares, post_type):
        self.post_id = post_id
        self.post_date = post_date
        self.candidate = candidate
        self.post_msg = post_msg
        self.no_comment = no_comment
        self.no_likes = no_likes
        self.no_shares = no_shares
        self.post_type = post_type
class Comments(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    post_id = db.Column(db.String(), index=True)
    comment_date =  db.Column(db.DateTime())
    candidate = db.Column(db.String(), index=True)
    comment_msg = db.Column(db.String())
    comment_id = db.Column(db.String(), index=True)
    like_count = db.Column(db.Integer())
    commenter_id = db.Column(db.String(), index=True)
    commenter_name = db.Column(db.String(), index=True)

    def __init__(self, post_id, comment_date, candidate, comment_msg, comment_id, like_count, commenter_id, commenter_name):
        self.post_id = post_id
        self.comment_date = comment_date
        self.candidate = candidate
        self.comment_msg = comment_msg
        self.comment_id = comment_id
        self.like_count = like_count
        self.commenter_id = commenter_id
        self.commenter_name = commenter_name
