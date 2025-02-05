import re, requests, csv, os
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine, Column, String, Date, Time, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy import Table, MetaData

chrome_options = Options()
chrome_options.add_argument("--headless")
DRIVER = webdriver.Chrome(options=chrome_options)

AVAILABLE_CINEMAS = {
    'UCI': 'https://www.ucicinemas.it/cinema/liguria/genova/uci-cinemas-fiumara-genova/',
    'TheSpace': 'https://www.thespacecinema.it/al-cinema/genova',
    'Circuito': 'https://circuitocinemagenova.com/programmazione-settimanale/'}
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

Base = declarative_base()

DB_TABLE = os.getenv('DB_TABLE')

db_config = {
    'host': os.getenv('DB_HOST'), 
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

class Timetable(Base):
    __tablename__ = DB_TABLE

    idx = Column(Integer, primary_key=True, autoincrement=True, name='id')
    cinema = Column(String, nullable=True)
    title = Column(String, nullable=True)
    language = Column(String, nullable=True)
    link = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    time = Column(Time, nullable=True)

class Database():
    def __init__(self):
        self.timetable = []

    def clean_title(self, title):
        """Clean the movie title."""

        title = title.lower()
        if title.endswith('autism friendly'):
            title = title[:-16]
        elif title.endswith('al cinema con te'):
            title = title[:-19]
        elif title.endswith('evento contro il bullismo'):
            title = title[:-26]
        title = re.sub(r'[\:\-–]', '', title)
        title = re.sub(r'\s{2,}', ' ', title)
        title = re.sub(r'\s+\([12][09][0-9][0-9]\)', '', title)
        return title.strip()

    def respond(self, cinema: str, href=None):
        """Send a request to the cinema website and return the response."""

        if href:
            url = href
        else:
            url = AVAILABLE_CINEMAS[cinema]
        if cinema == 'TheSpace':
            DRIVER.get(url)
            try:
                element = WebDriverWait(DRIVER, 5).until(EC.presence_of_element_located((By.ID, "filmlist__data")))
            except:
                print("Loading timed out.")
                return None
            finally:
                page_source = DRIVER.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                return soup
        else:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
            else:
                print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
                return None

    def timetable_UCI(self):
        """Crawl timetable data from UCI Cinemas website."""

        soup = self.respond('UCI')
        if soup:

            dates = soup.select('#showtimes-venue-container > header > div > ul > li > a')
            dates = [date['data-day'] for date in dates]

            data = []
            for date in dates:
                movies = soup.select(f'#movie_{date} > div.showtimes__show')

                date = [date[i:i+2] for i in range(0, len(date), 2)]
                date = f"20{date[2]}-{date[1]}-{date[0]}"

                for movie in movies:
                    titles = movie.select('span.movie-name > a')
                    showtimes = movie.select('ul.showtimes__movie__shows > li > a')
                    showtimes = [showtime.get_text() + ":00" for showtime in showtimes]
                    for title in titles:
                        name = title.get_text().lower()
                        if name.startswith('(o.v.)'):
                            name = name[7:]
                            language = 'en'
                        elif name.startswith('(jp)'):
                            name = name[5:]
                            language = 'jp'
                        elif name.startswith('(kor)'):
                            name = name[6:]
                            language = 'kor'
                        else:
                            language = 'it'
                        href = 'https://www.ucicinemas.it' + title['href']
                        
                        updated = False
                        for movie in data:
                            if movie['title'] == name and movie['language'] == language:
                                if date in movie['dates']:
                                    movie['dates'][date] += showtimes
                                else:
                                    movie['dates'][date] = showtimes
                                updated = True
                                break
                        if not updated:
                            
                            record = {"cinema": 'UCI Fiumara', 'title': self.clean_title(name), 'language': language, 'dates': {date: showtimes}, 'link': href}
                            data.append(record)
            
            for record in data:
                for date in record['dates']:
                    self.timetable += [{"cinema": record["cinema"], 
                                        "title": record['title'], 
                                        "language": record['language'], 
                                        "link": record['link'], 
                                        "date": date, 
                                        "time": time} for time in record['dates'][date]]
            return True
 
    def timetable_the_space(self):
        """Crawl timetable data from TheSpace Cinema website."""
        
        def process_time(time_evement):
            date = time_evement.get('datetime')
            time = time_evement.get_text() + ":00"
            return (date, time)

        soup = self.respond('TheSpace')
        if soup:
            movies = soup.select('#filmlist__data > div.filmlist__item') 
            movies = [movie for movie in movies if movie.get('data-hidden') == 'false']
            data = []
            for movie in movies:
                title = movie.select('div.filmlist__info > div > a > span')[0].get_text().lower()
                if title.endswith('versione originale'):
                    title = title[:-21]
                    language = 'en'
                else:
                    language = 'it'
                
                href = 'https://www.thespacecinema.it' + movie.select('div.filmlist__info > div > a')[0].get('href')
                
                timetable = movie.select('div.day')
                date = [item.select('time.date') for item in timetable]
                time = [item.select('time.default') for item in timetable]
                for day in time:
                    for timeslot in day:
                        (date, time) = process_time(timeslot)
                        
                        self.timetable += [{
                            'cinema': 'TheSpace', 
                            'title': self.clean_title(title), 
                            'language': language, 
                            'link': href, 
                            'date': date, 
                            'time': time}]

            return True

    def timetable_circuito(self):
        """Crawl timetable data from Circuito Cinema Genova website."""

        soup = self.respond('Circuito')
        if soup:
            cinemas = soup.select('div.cinema_row')
            for cinema in cinemas:
                name = cinema.select('h2')[0].get_text()
                films = cinema.select('div.single-film')
                for film in films:
                    title = film.select('p')[0].get_text().lower().strip()
                    if title.endswith('- v. o.'):
                        title = title[:-8]
                        language = 'en'
                    elif title.endswith('- vers.orig.sott.it'):
                        title = title[:-20]
                        language = 'en'
                    elif title.endswith('vers. orig. sott.'):
                        title = title[:-18]
                        language = 'en'
                    else:
                        language = 'it'
                    days = film.select('div.day_block')
                    if not days:
                        continue
                    else:
                        href = film.select('a.theme-btn')[0].get('href')
                        data = {}
                        for day in days:
                            date = day.select('h4')[0].get_text().split(' ')
                            today_year = datetime.now().year
                            month_mapping = {'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04', 'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08', 'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'}
                            date = f'{today_year}-{month_mapping[date[-1]]}-{date[1]}'
                            hours = day.select('span.start_hour')
                            hours = [hour.get_text().strip() + ':00' for hour in hours]
                            data[date] = hours
                            for time in hours:
                                self.timetable += [{
                                    'cinema': 'Circuito ' + name, 
                                    'title': self.clean_title(title), 
                                    'language': language, 
                                    'link': href, 
                                    'date': date, 
                                    'time': time}]
            return True

    def crawl_timetable(self):
        """Crawl timetable data from all cinema websites."""

        for cinema in AVAILABLE_CINEMAS:
            print(f'Crawling {cinema}...')
            if cinema == 'UCI':
                self.timetable_UCI()
            if cinema == 'Circuito':
                self.timetable_circuito()
            if cinema == 'TheSpace':
                self.timetable_the_space()

        return self.timetable

    def write_timetable_to_csv(self, filename='timetable.csv'):
        """Write timetable data to a CSV file."""

        with open(filename, "w", newline="", encoding='utf-8') as f:
            title = self.timetable[0].keys()
            cw = csv.DictWriter(f, title, delimiter=',')
            cw.writeheader()
            cw.writerows(self.timetable)
        return True
    
    def insert_timetable_data(self):
        """Insert timetable data into the database."""

        engine = create_engine(f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}")
        Base.metadata.create_all(engine)
        metadata = MetaData()
        timetable_ = Table(DB_TABLE, metadata, autoload_with=engine)

        with engine.connect() as connection:
            transaction = connection.begin()  # Start transaction
            try:
                connection.execute(timetable_.delete())  # Delete all rows
                transaction.commit()  # Commit changes
                print("All records deleted successfully.")
            except Exception as e:
                transaction.rollback()  # Rollback on error
                print(f"Error: {e}")
        connection.close()

        with engine.connect() as connection:
            trans = connection.begin()
            connection.execute(timetable_.insert(), self.timetable)
            trans.commit()
        connection.close()    
        return True
    

def run(event, context):
    db = Database()
    result = db.crawl_timetable()
    if result:
        db.insert_timetable_data()

if __name__ == '__main__':
    db = Database()
    result = db.crawl_timetable()
    print(result)
    # db.write_timetable_to_csv()
    db.insert_timetable_data()

