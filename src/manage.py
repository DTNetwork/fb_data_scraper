#!/usr/bin/env python
from flask import Flask
from flask_script import Manager, Server
from models import db, Posts, Comments

app = Flask(__name__)
app.config.from_object('settings.Config')
db.init_app(app)
manager = Manager(app)

@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """

    return dict(app=app, db=db, Posts = Posts, Comments=Comments)


@manager.command
def createdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    print "here"
    db.create_all()

if __name__ == "__main__":
	manager.run()