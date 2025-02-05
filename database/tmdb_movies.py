from tmdbv3api import TMDb, Movie
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings
from extract import fetch_data
import hashlib, os


TMDB_API_KEY = os.getenv("TMDB_API_KEY")
MISTRALAI_API_KEY = os.getenv("MISTRALAI_API_KEY")
DB_TABLE = os.getenv("DB_TABLE")

tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
movie = Movie()

embeddings = MistralAIEmbeddings(api_key=MISTRALAI_API_KEY)

persist_directory = 'chroma/' # Chroma vector store
vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

def hash_title(s):
    """Hash a string and return the first 8 digits."""

    hash_s = int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
    return str(hash_s) 


def find_movie(title):
    """Search for a movie in TMDB database and return a Document object with movie details."""
    
    try:
        result = movie.search(title)[0]
    except TypeError:
        print(f'Movie {title} not found')
        description = 'Movie not found'
        info = ''
    else:
        result = movie.details(result.id)
        genres = [genre['name'] for genre in result['genres']]
        
        try:
            country = result['production_countries'][0]['name']
        except TypeError:
            country = ''
        
        cast = [person.name for person in result['casts']['cast']]
        duration = result['runtime'] if result['runtime'] > 0 else ''
        director = [person.name for person in result['casts']['crew'] if person.job == 'Director']
        orig_title = f'(original title: {result['original_title']})' if result['original_title'] != result['title'] else ''
        description = f"""{result['title']} {orig_title}\n\n{result['overview']}"""
        info = f"""Title: {result['title']} {orig_title}
    Movie is released in {country} on {result['release_date']} with duration of {duration} minutes.
    Director: {", ".join(director)}
    Cast: {", ".join(cast[:7])}
    Rating: {result['vote_average']} (TMDb)
    Genres: {", ".join(genres)}"""

    docs = [Document(page_content=description, metadata={'source': 'TMDB', 'type': 'description', 'sql_db_title': title}, id=hash_title(title+'d')),
            Document(page_content=info, metadata={'source': 'TMDB', 'type': 'info', 'sql_db_title': title}, id=hash_title(title+'i'))]
    return docs

def fill_chroma_db(titles: dict[str] = None):
    """Fill the Chroma database with movie details from TMDB database."""

    if not titles:
        query = f"SELECT DISTINCT title FROM {DB_TABLE}"
        titles = fetch_data(query)
    docs = []
    for row in titles:
        title, idx = row['title'], hash_title(row['title']+'d')
        search = vectordb.get(limit=1, ids=idx)["ids"]
        if not search:
            doc = find_movie(title)
            docs += doc
    if docs:
        vectordb.from_documents(docs, embedding=embeddings, persist_directory=persist_directory)
    return True


if __name__ == '__main__':
    fill_chroma_db()
    print(vectordb._collection.count())
