import sqlalchemy
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from nt_chat.config import (MODEL_NAME, OPENAI_KEY, SQLITE_DB_PATH,
                            TOP_K_RESULTS, UNICODE_PLUGIN_PATH)
from nt_chat.prompts import _DECIDER_TEMPLATE, DEFAULT_TEMPLATE
from nt_chat.sql_chain import SQLDatabaseSequentialChain

debug_mode = True


def db_uri(path: str):
    return f"sqlite:///{path}"


def make_db(num_sample_rows=2):
    """It is optimal to include a sample of rows from the tables in the prompt
    to allow the LLM to understand the data before providing a final query.
    """
    engine = sqlalchemy.create_engine(db_uri(SQLITE_DB_PATH))

    @sqlalchemy.event.listens_for(engine, "connect")
    def recv_connect(connection, _):
        """This extension is important because it allows us
        to do a case insensitive search with Greek characters"""
        connection.enable_load_extension(True)
        connection.load_extension(UNICODE_PLUGIN_PATH)
        connection.enable_load_extension(False)

    return SQLDatabase(
        engine,
        sample_rows_in_table_info=num_sample_rows,
    )


def make_llm(stream=False, manager=None):
    """Initialize the LLM
    Available models: https://platform.openai.com/docs/models/
    """
    return ChatOpenAI(
        temperature=0.01,
        verbose=debug_mode,
        callback_manager=manager,
        openai_api_key=OPENAI_KEY,
        model_name=MODEL_NAME,
        max_tokens=None,
        streaming=stream,
    )


def make_prompt():
    return PromptTemplate(
        input_variables=["input", "table_info", "dialect", "top_k"],
        template=DEFAULT_TEMPLATE,
    )


def make_decider_prompt():
    return PromptTemplate(
        input_variables=["query", "table_names"],
        template=_DECIDER_TEMPLATE,
        output_parser=CommaSeparatedListOutputParser(),
    )


db = make_db()
prompt = make_prompt()


def make_chain(stream=False, return_intermediate_steps=False, top_k=TOP_K_RESULTS):
    return SQLDatabaseSequentialChain.from_llm(
        make_llm(stream=stream),
        db,
        verbose=True,
        use_query_checker=True,
        return_intermediate_steps=return_intermediate_steps,
        query_prompt=prompt,
        top_k=top_k,
        return_direct=False,
    )
