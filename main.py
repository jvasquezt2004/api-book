from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from fastapi import Depends
from schemas import SearchParams, SearchResult, SearchResponse, ErrorResponse, GetSummaryParams
import wikipedia
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.readers.wikipedia import WikipediaReader
from llama_index.core.llms import ChatMessage, MessageRole

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables")

from postgrest.exceptions import APIError

client = create_client(SUPABASE_URL, SUPABASE_KEY)
client.postgrest.timeout = 60
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = SupabaseVectorStore(
    client=client,
    table_name="documents",
    embedding=embeddings,
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/get_summary")
async def get_summary(params: GetSummaryParams = Depends()):
    def get_wikipedia_content(title: str, sentences_per_section: int = 10, max_chars: int = 3000):
        try:
            page_results = wikipedia.search(title, results=1) 
            if not page_results:
                return ""
            page_title_to_try = page_results[0]
            page = None

            try:
                page = wikipedia.page(page_title_to_try, auto_suggest=False, redirect=True)
            except wikipedia.exceptions.DisambiguationError as e:
                relevant_option = next((opt for opt in e.options if title.lower() in opt.lower() or "(book)"))
                if relevant_option:
                    page = wikipedia.page(relevant_option, auto_suggest=False, redirect=True)
                else:
                    return ""
            except wikipedia.exceptions.PageError:
                return ""
            except Exception as e_page:
                return ""

            if page and hasattr(page, "summary"):
                summary_text = wikipedia.summary(page.title, sentences=sentences_per_section, auto_suggest=False)
                if len(summary_text) > max_chars:
                    summary_text = summary_text[:max_chars]
                return summary_text.strip()
            else:
                return ""

        except Exception as e_summary:
            return ""

    try:
        llm = OpenAI(model="gpt-4.1-nano", temperature=0.7, max_tokens=1600)
        Settings.llm = llm
    except Exception as e_llm:
        llm = None

    system_prompt = (
    "You are an expert librarian and a skilled summary writer. Your task is to write comprehensive, engaging, and strictly spoiler-free book summaries for catalogs. "
    "The summary must be structured into exactly FOUR distinct paragraphs. "
    "Each paragraph should ideally be between 100 and 250 words. "
    "The summary must capture the main themes, an overview of the plot (without revealing spoilers, major twists, or the ending), key characters (if central to a non-spoiler overview), and the general tone of the work. "
    "You must use all the information provided: the book title, the original description from the dataset, and any supplemental context from Wikipedia. Synthesize this information effectively. "
    "CRITICALLY IMPORTANT: DO NOT REVEAL ANY SPOILERS, major plot twists, or the ending of the book. Maintain a neutral and informative tone suitable for a catalog."
    "\n\nIf, even with all the provided information, you cannot create a meaningful, accurate, and spoiler-free summary adhering to the requested length (4 paragraphs, 100-250 words each) and structure, "
    "or if the book is entirely unfamiliar and the provided details are grossly insufficient for such a summary, "
    "please respond with the exact phrase: UNKNOWN_BOOK_INFO"
    )

    user_prompt_template_str = (
    "Please generate a detailed, four-paragraph, spoiler-free summary for the following book. "
    "Aim for each paragraph to be between 100 and 250 words.\n\n"
    "Book Title: {title}\n\n"
    "Original Description (from dataset):\n{original_description}\n\n"
    "Supplemental Information (from Wikipedia):\n{wikipedia_context}\n\n"
    "Summary (FOUR paragraphs, 100-250 words each, ABSOLUTELY NO SPOILERS):"
)

    wikipedia_context = get_wikipedia_content(params.title)
    
    user_content_formatted = user_prompt_template_str.format(
        title=params.title,
        original_description = params.original_description,
        wikipedia_context = wikipedia_context if wikipedia_context else "No Wikipedia context available"
    )

    messages_for_llama_index = [
        ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
        ChatMessage(role=MessageRole.USER, content=user_content_formatted)
    ]

    try:
        response = Settings.llm.chat(messages_for_llama_index)
        summary_text = str(response.message.content).strip()
        if summary_text.upper() == "UNKNOWN_BOOK_INFO" or not summary_text:
            return {
                "error": "Unable to generate summary for this book",
                "summary_text": ""
            }
        else:
            return {
                "error": "",
                "summary_text": summary_text
            }
    except Exception as e:
        return {
            "error": str(e),
            "summary_text": ""
        }

@app.get("/search")
async def search(params: SearchParams = Depends()):
    try:
        k = params.limit + params.offset
        search_kwargs = {}
        if params.dominant_sentiment:
            search_kwargs["filter"] = {"metadata": {"dominant_sentiment": params.dominant_sentiment}}
        
        k = min(k, 50)
        
        docs = vectorstore.similarity_search(
            query=params.query, 
            k=k,
            **search_kwargs
        )
        
        end_idx = min(params.offset + params.limit, len(docs))
        sliced = docs[params.offset:end_idx] if params.offset < len(docs) else []
        
        results = [
            SearchResult(
                uuid=doc.metadata.get("isbn") or doc.metadata.get("uuid") or "",
                content=doc.page_content,
                metadata=doc.metadata
            )
            for doc in sliced
        ]
        return SearchResponse(
            results=results,
            limit=params.limit,
            offset=params.offset,
            total=len(docs)
        )
    except APIError as e:
        error_message = str(e)
        if "statement timeout" in error_message:
            return ErrorResponse(
                error="Search query timed out. Please try with a more specific query or without dominant sentiment filtering.",
                details=error_message
            )
        return ErrorResponse(
            error="Database query error",
            details=error_message
        )
    except Exception as e:
        return ErrorResponse(
            error="An unexpected error occurred",
            details=str(e)
        )
