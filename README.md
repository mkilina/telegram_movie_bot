# LLM-Powered Chatbot with RAG  

A Telegram bot that uses Retrieval-Augmented Generation (RAG) to provide up-to-date information about cinemas in Genova. It allows users to chat about currently available movies, timetables, and general film-related queries.  

## What It Uses  

- **Mistral AI LLM** – Generates responses based on retrieved data.  
- **LangChain & LangGraph** – Used to build an LLM agent that utilizes tools.  
- **SQL Database** – Stores cinema timetables.  
- **Chroma Vector Store** – Stores movie details such as director, plot, cast, and duration.  
- **Telegram Bot API** – Enables interaction through Telegram.  

## Setup  

Clone the repository and navigate to the project directory:  

```bash
git clone https://github.com/mkilina/telegram_movie_bot.git  
cd telegram_movie_bot
```

Install dependencies:

```bash
pip install -r requirements.txt  
```

Set up environment variables by creating a .env file in the root directory:

```python
TELEGRAM_BOT_TOKEN=your_token_here  
MISTRAL_API_KEY=your_key_here  
DATABASE_URL=your_db_url_here  
...
```

### Populating the Database

Before using the chatbot, you need to populate the databases with up-to-date movie information. This is done by crawling cinema websites and fetching additional movie details from the TMDB API.

Run the following script to update the databases:

```bash
python database/update_all.py
```

The database structure is described in `database/crawl.py`, in the class named `Timetable`.

This script performs the following actions:

* Scrapes cinema websites (currently supports only cinemas in Genova, Italy) to fetch movie timetables.
* Stores the timetable data in the SQL database.
* Queries the TMDB API for movie details (such as director, cast, plot, and duration).
* Stores this additional movie information in the Chroma vector database for retrieval.

Once the databases are populated, you can proceed with running the chatbot.

### Starting the bot

To start the bot on Telegram:

```bash
python telegram_bot.py  
```

To use the bot via CLI instead of Telegram:

```bash
python terminal_bot.py  
```

## Usage
### General Chat
The bot can chat about anything, but it has specialized tools to provide cinema-related information.

### Movie Timetable Queries
If you want to know information about movies currently in cinemas in Genova, the bot will use an SQL database to retrieve the data. You can specify:

* The *language* of the movie
* The *cinema* you want to visit
* The *day* and/or *time* you prefer
* The *title* of the movie

**Example Queries:**

>*What movies are playing in Genova today?*
>
>*Are there any English-language films this weekend?*
>
>*Show me the schedule for "Oppenheimer" at The Space Cinema.*
>
The LLM will generate an SQL query, execute it, and return a natural language response.

### Movie Information Queries

You can ask about movies based on various criteria. The bot will use the vector database to retrieve relevant information.

**Example Queries:**

>*What are some good thriller movies?*
>
>*Which movies were directed by Christopher Nolan?*
>
>*List movies starring Leonardo DiCaprio.*
>
>*Give me a short summary of "Inception".*
>
>*How long is "The Godfather"?*

The LLM will find top-n relevant documents and extract form them pieces of information necessary to answer the question.

## Live Bot
You can interact with the chatbot [here](https://t.me/htn_dialogue_bot).
