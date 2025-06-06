from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from fastapi import Depends
from schemas import SearchParams, SearchResult, SearchResponse, ErrorResponse, GetSummaryParams, UploadBookParams, ClassifyBookParams
import wikipedia
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.readers.wikipedia import WikipediaReader
from llama_index.core.llms import ChatMessage, MessageRole
import uuid
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from transformers import pipeline

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

@app.post("/upload_book")
async def upload_book(params: UploadBookParams):
    try:
        # Extraer los datos del parámetro
        content = params.content
        metadata = params.metadata
        
        # Verificar si el libro ya existe buscando por título en metadata
        title = metadata.get('title')
        if title:
            # Consultar Supabase para buscar libros con el mismo título
            try:
                # Usar PostgreSQL JSON query para buscar en el campo metadata
                response = client.table("documents") \
                    .select("id, metadata") \
                    .filter("metadata->>title", "eq", title) \
                    .execute()
                
                if hasattr(response, 'data') and response.data:
                    # El libro ya existe en la base de datos
                    return {
                        "success": False, 
                        "error": "El libro ya existe en la base de datos", 
                        "existing_document_id": response.data[0].get("id")
                    }
            except Exception as search_error:
                # Alternativa si la sintaxis anterior no funciona
                try:
                    # Obtener todos los documentos y filtrar manualmente
                    response = client.table("documents").select("id, metadata").execute()
                    
                    if hasattr(response, 'data') and response.data:
                        for doc in response.data:
                            doc_metadata = doc.get("metadata", {})
                            if isinstance(doc_metadata, dict) and doc_metadata.get("title") == title:
                                return {
                                    "success": False, 
                                    "error": "El libro ya existe en la base de datos", 
                                    "existing_document_id": doc.get("id")
                                }
                except Exception as e:
                    # Si falla la búsqueda, continuamos con la inserción normal
                    pass
        
        # Generar un UUID para el documento (siempre usar UUID válido para la columna id)
        document_id = str(uuid.uuid4())
        
        document_data = {
            "id": document_id,
            "content": content,
            "metadata": metadata
        }
        
        # Generar embeddings solo si hay contenido
        if content:
            try:
                # Generar embedding usando el modelo configurado
                text_embedding = embeddings.embed_query(content)
                
                # Si estamos usando vectorstore, usamos su método
                # Usamos los IDs que ya hemos generado para asegurar consistencia
                ids = vectorstore.add_documents(
                    documents=[content],
                    metadatas=[metadata],
                    ids=[document_id]
                )
                
                return {"success": True, "document_id": document_id}
                
            except Exception as e:
                # Inserción directa con embedding generado
                document_data["embedding"] = text_embedding
                response = client.table("documents").insert(document_data).execute()
                
                if hasattr(response, 'error') and response.error:
                    return {"success": False, "error": response.error.message}
                
                return {"success": True, "document_id": response.data[0].get("id") if response.data else None}
        else:
            # Si no hay contenido, insertar sin embeddings
            response = client.table("documents").insert(document_data).execute()
            
            if hasattr(response, 'error') and response.error:
                return {"success": False, "error": response.error.message}
            
            return {"success": True, "document_id": response.data[0].get("id") if response.data else None}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

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
    except Exception as e:
        return ErrorResponse(error=str(e))

@app.post("/classify_book")
async def classify_book(params: ClassifyBookParams):
    try:
        # Inicializar valores de salida
        result = {
            "success": True,
            "content": params.content[:100] + "..." if len(params.content) > 100 else params.content  # Solo para confirmar
        }
        
        # Obtener la categoría usando un clasificador zero-shot si no se proporcionó
        category = params.category
        if not category:
            try:
                # Inicializar el clasificador zero-shot
                classifier = pipeline("zero-shot-classification", 
                                     model="facebook/bart-large-mnli")
                
                # Definir posibles categorías de libros
                categories = [
                    "Fiction", "Non-fiction", "Science Fiction", "Fantasy", "Mystery", 
                    "Romance", "Biography", "History", "Poetry", "Self-help",
                    "Business", "Travel", "Religion", "Science", "Philosophy",
                    "Art", "Thriller", "Horror", "Young Adult", "Children"
                ]
                
                # Obtener solo los primeros 1024 tokens para el clasificador
                text_sample = params.content[:4000] if len(params.content) > 4000 else params.content
                
                # Clasificar el contenido
                classification = classifier(text_sample, categories)
                
                # Obtener la categoría con mayor puntuación
                category = classification['labels'][0]
                score = classification['scores'][0]
                
                result["category"] = category
                result["category_score"] = score
                
            except Exception as e:
                result["category_error"] = str(e)
        else:
            result["category"] = category
            result["category_note"] = "Provided by user"
        
        # Obtener el sentimiento dominante si no se proporcionó
        sentiment = params.dominant_sentiment
        if not sentiment:
            try:
                # Usar NLTK para análisis de sentimiento
                sia = SentimentIntensityAnalyzer()
                
                # Obtener muestra del texto para análisis
                text_sample = params.content[:5000] if len(params.content) > 5000 else params.content
                
                # Analizar el sentimiento
                sentiment_scores = sia.polarity_scores(text_sample)
                
                # Determinar el sentimiento dominante y su valor
                compound_score = sentiment_scores['compound']
                if compound_score >= 0.05:
                    dominant_sentiment = "joy"
                elif compound_score <= -0.05:
                    dominant_sentiment = "fear"
                else:
                    dominant_sentiment = "neutral"
                
                result["dominant_sentiment"] = dominant_sentiment
                result["sentiment_value"] = compound_score
                
            except Exception as e:
                result["sentiment_error"] = str(e)
        else:
            result["dominant_sentiment"] = sentiment
            result["sentiment_note"] = "Provided by user"
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}
