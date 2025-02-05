from dotenv import load_dotenv
load_dotenv()

from LLM.agent import app

if __name__ == "__main__":
    config = {"configurable": {"thread_id": 'user_id'}}
    while True:
        user_input = input("You: ").strip()
        messages = app.invoke({"messages": [("human", user_input)]}, config=config)
        llm_answer = messages['messages'][-1].content
        print('Agent:', llm_answer)