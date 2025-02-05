from dotenv import load_dotenv
load_dotenv()

from crawl import Database
from tmdb_movies import fill_chroma_db

db = Database()
result = db.crawl_timetable()
db.insert_timetable_data()

titles = []
for dictionary in result:
    title = dictionary['title']
    item = {'title': title}
    if item not in titles:
        titles.append(item)

fill_chroma_db(titles)