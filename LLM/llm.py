from typing_extensions import TypedDict
from typing import Optional
from pydantic import BaseModel, Field
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_core.tools import tool
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_chroma import Chroma
from httpx import HTTPStatusError
import time, os
from datetime import datetime
from database.extract import get_db_engine


MISTRALAI_API_KEY = os.getenv("MISTRALAI_API_KEY")

embeddings = MistralAIEmbeddings(api_key=MISTRALAI_API_KEY)
llm = ChatMistralAI(model="mistral-large-latest", temperature=0, api_key=MISTRALAI_API_KEY)

engine = get_db_engine() # SQL database
db = SQLDatabase(engine)

persist_directory = 'database/chroma/' # Chroma vector store
vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

def load_prompt(filename):
    with open(f"LLM/prompts/{filename}.txt", "r") as f:
        return f.read()

prompt_template_SQL = load_prompt("generate_sql")
prompt_template_relative_dates = load_prompt("relative_dates")

class State(TypedDict):
    question: str
    query: Optional[str] = ''
    result: Optional[str] = ''
    answer: Optional[str] = ''

class QueryOutput(BaseModel):
    """Generate an SQL query."""

    query: str = Field(description="Syntactically valid SQL query.")

@tool
def date_tool(state: State) -> str:
    """Rewrites user input resolving all relative date and time expressions."""
    
    today = datetime.now()
    today_date = today.strftime("%Y-%m-%d")
    today_time = today.strftime("%H:%M")
    day_of_week = today.strftime("%A")
    input = state['question']
    updated_query = resolve_relative_date(input, today_date, today_time, day_of_week).content

    return {'question': updated_query}

@tool
def retrieve_movie_info(state: State) -> str:
    """Retrieve information about movies stored in the database. 
    Use this tool whenever a user asks about specific movies, movies of a certain genre, release dates, durations, ratings, cast, directors, or general movie-related queries. 
    Do not use this tool for timetables of the movies.
    This tool provides accurate information from the vector database rather than relying on general knowledge."""
	
    input = state['question']
    try:
        docs = vectordb.similarity_search(input,k=3)
    except HTTPStatusError:
        time.sleep(2)
        docs = vectordb.similarity_search(input,k=3)

    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in docs)    
    
    return {'result': serialized}

def write_query(state: State) -> dict:
    """Generate SQL query to fetch information about movies timetable."""
    
    input = state['question']
    prompt = prompt_template_SQL.format(dialect=db.dialect, top_k=10, table_info=db.get_table_info(), input=input)
    structured_llm = llm.with_structured_output(QueryOutput)
    try:
        result = structured_llm.invoke(prompt)
    except HTTPStatusError:
        print('sleeping in write_query')
        time.sleep(2)
        result = structured_llm.invoke(prompt)
    
    return {'query': result.query}

def execute_query(state: State):
    """Execute SQL query."""
    
    query = state['query']
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    result = execute_query_tool.invoke(query)
    return {'result': result}

@tool
def query_timetable_db(state: State):  
    """Access the database to retrieve information about movies timetable. 
    This tool will first generate an SQL query based on the user's question and then execute it to fetch the required information."""
    
    query = write_query(state)
    result = execute_query(query)

    return result

def resolve_relative_date(user_prompt: str, today_date: str, today_time: str, day_of_week: str) -> str:
    """Use an LLM to resolve relative dates and rewrite user's message given today's date and day of the week."""
    
    prompt = prompt_template_relative_dates.format(today_date=today_date, today_time=today_time, day_of_week=day_of_week, user_prompt=user_prompt)
    try:
        updated_prompt = llm.invoke(prompt) 
    except HTTPStatusError:
        print('sleeping in resolve_relative_date')
        time.sleep(2)
        updated_prompt = llm.invoke(prompt) 
    return updated_prompt

tools = [date_tool, retrieve_movie_info, query_timetable_db]
llm_with_tools = llm.bind_tools(tools)
