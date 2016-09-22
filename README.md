# FB Data Scraper

Can be used to get Posts and Comments using FB API.

## Setup

To run the code, setup using following commands in a terminal(Linux/Mac)<sup>**</sup>

* `git clone https://github.com/scottydelta/fb_data_scraper.git`
* `cd fb_data_scraper`
* `virtualenv .env`
* `source .env/bin/activate`
* `cd src`
* `pip install -r requirements`

<sup>**</sup>Assuming that PostgreSQL, pip and virtualenv are installed.

## How to use it?

* Edit the `settings.py` and add/change the DB URI(DB name) or db user or password for Postgres.
* Get ACCESS_TOKEN from Facebook and insert in the `settings.py`.
* Add the list of pages you want to scrape.
* Execute `python manage.py createdb` to create the tables and initialize the tables<sup>**</sup>
* Execute `python fb_data.py` to execute the script to get posts and comments from a page.

<sup>**</sup>Assuming the Database is already created in Postgres
