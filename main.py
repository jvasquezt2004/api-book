from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client
from langchain_openai import OpenAIEmbeddings  # updated to langchain_openai package
from langchain_community.vectorstores import SupabaseVectorStore  # updated to community package
from fastapi import Depends, HTTPException, status
from schemas import SearchParams, SearchResult, SearchResponse, ErrorResponse

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

# Load environment variables and initialize Supabase vector store
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables")

# Initialize Supabase client with a longer timeout
from postgrest.exceptions import APIError

# Increase timeout to 60 seconds
client = create_client(SUPABASE_URL, SUPABASE_KEY)
client.postgrest.timeout = 60  # increase timeout to 60 seconds
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")  # use OpenAI large embeddings
vectorstore = SupabaseVectorStore(
    client=client,
    table_name="documents",
    embedding=embeddings,
)

# Schemas moved to schemas.py

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/search")
async def search(params: SearchParams = Depends()):
    try:
        # fetch extra docs to apply offset
        k = params.limit + params.offset
        search_kwargs = {}
        if params.dominant_sentiment:
            search_kwargs["filter"] = {"metadata": {"dominant_sentiment": params.dominant_sentiment}}
        
        # Limit k to prevent excessive search time
        k = min(k, 50)  # Cap at 50 to avoid timeouts
        
        docs = vectorstore.similarity_search(
            query=params.query, 
            k=k,
            **search_kwargs
        )
        
        # Apply pagination (handle case where fewer docs than expected are returned)
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
