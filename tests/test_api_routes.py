import pytest
from fastapi.testclient import TestClient
from main import app
import uuid
import json

client = TestClient(app)

def test_read_root():
    """Prueba la ruta raíz de la API"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello" in response.json()

def test_search_no_query():
    """Prueba la ruta /search con un error: parámetro query faltante"""
    response = client.get("/search")
    assert response.status_code == 422  # Unprocessable Entity debido a parámetros faltantes

def test_search_with_query():
    """Prueba la ruta /search con una consulta válida"""
    response = client.get("/search?query=aventuras")
    assert response.status_code == 200
    assert "results" in response.json()
    assert "limit" in response.json()
    assert "offset" in response.json()
    assert "total" in response.json()

def test_search_with_sentiment_filter():
    """Prueba la ruta /search con filtro de sentimiento"""
    response = client.get("/search?query=aventuras&dominant_sentiment=joy")
    assert response.status_code == 200
    assert "results" in response.json()

def test_search_pagination():
    """Prueba la paginación en la ruta /search"""
    response = client.get("/search?query=literatura&limit=5&offset=2")
    assert response.status_code == 200
    assert "results" in response.json()
    assert response.json()["limit"] == 5
    assert response.json()["offset"] == 2

def test_upload_book_missing_content():
    """Prueba la ruta /upload_book con error: contenido faltante"""
    test_data = {
        "metadata": {
            "title": "Libro de prueba"
        }
    }
    response = client.post("/upload_book", json=test_data)
    assert response.status_code == 422  # Unprocessable Entity

def test_upload_book_duplicate_title():
    """Prueba la ruta /upload_book con un título ya existente"""
    # Primero intentamos encontrar un libro existente para usar su título
    search_response = client.get("/search?query=Quijote")
    if search_response.status_code == 200 and len(search_response.json()["results"]) > 0:
        existing_title = search_response.json()["results"][0]["metadata"]["title"]
        
        test_data = {
            "content": "Este es un libro de prueba con título duplicado",
            "metadata": {
                "title": existing_title,
                "isbn": "9999999999",
                "authors": "Test Author"
            }
        }
        response = client.post("/upload_book", json=test_data)
        assert response.status_code == 400 or "error" in response.json()
        if "error" in response.json():
            assert "libro ya existe" in response.json()["error"].lower()

def test_upload_book_success():
    """Prueba la ruta /upload_book con un libro nuevo (El Periquillo Sarniento)"""
    unique_title = f"El Periquillo Sarniento - Test {uuid.uuid4()}"
    test_data = {
        "content": """El Periquillo Sarniento es una novela picaresca mexicana escrita por José Joaquín Fernández de Lizardi, 
        publicada entre 1816 y 1831. Es considerada la primera novela hispanoamericana. 
        La obra narra en primera persona las aventuras y desventuras de Pedro Sarmiento, 
        conocido como "el Periquillo Sarniento", un joven criollo de la Ciudad de México.""",
        "metadata": {
            "title": unique_title,
            "isbn": str(uuid.uuid4()),
            "authors": "José Joaquín Fernández de Lizardi",
            "categories": "Fiction",
            "published_year": 1816
        }
    }
    response = client.post("/upload_book", json=test_data)
    assert response.status_code == 200
    assert "success" in response.json()
    assert response.json()["success"] is True
    assert "document_id" in response.json()

def test_classify_book():
    """Prueba la ruta /classify_book con un fragmento de texto"""
    test_data = {
        "content": """El Periquillo Sarniento es una novela picaresca mexicana escrita por José Joaquín Fernández de Lizardi. 
        La obra utiliza la estructura narrativa de la novela picaresca española del Siglo de Oro, 
        pero aplicada al contexto mexicano de principios del siglo XIX."""
    }
    response = client.post("/classify_book", json=test_data)
    assert response.status_code == 200
    assert "success" in response.json()
    assert response.json()["success"] is True
    assert "category" in response.json()
    assert "dominant_sentiment" in response.json()

def test_classify_book_with_provided_values():
    """Prueba la ruta /classify_book con valores predefinidos"""
    test_data = {
        "content": "Este es un contenido de prueba",
        "category": "Fiction",
        "dominant_sentiment": "joy"
    }
    response = client.post("/classify_book", json=test_data)
    assert response.status_code == 200
    assert "success" in response.json()
    assert response.json()["category"] == "Fiction"
    assert response.json()["category_note"] == "Provided by user"
    assert response.json()["dominant_sentiment"] == "joy"
    assert response.json()["sentiment_note"] == "Provided by user"

def test_upload_and_search():
    """Test integrado: upload_book seguido de search para verificar que el libro aparezca"""
    # 1. Cargar un libro único
    unique_title = f"Libro Único de Prueba {uuid.uuid4()}"
    unique_content = f"Este es un contenido único para pruebas {uuid.uuid4()}"
    
    upload_data = {
        "content": unique_content,
        "metadata": {
            "title": unique_title,
            "isbn": str(uuid.uuid4()),
            "authors": "Autor de Prueba"
        }
    }
    upload_response = client.post("/upload_book", json=upload_data)
    assert upload_response.status_code == 200
    assert "success" in upload_response.json()
    
    # 2. Buscar el libro por su título único
    # Usamos una palabra clave única del contenido para la búsqueda
    unique_word = unique_content.split()[6]  # palabra única del contenido
    search_response = client.get(f"/search?query={unique_word}")
    assert search_response.status_code == 200
    
    # 3. Verificar si el libro aparece en los resultados
    found = False
    for result in search_response.json()["results"]:
        if unique_title == result["metadata"].get("title"):
            found = True
            break
    
    assert found, f"El libro '{unique_title}' no fue encontrado en los resultados de búsqueda"
