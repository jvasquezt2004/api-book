# API de Libros

API para gestionar y buscar libros con categorización automática y análisis de sentimientos utilizando FastAPI, Supabase y modelos de IA.

## Características

- **Búsqueda semántica**: Busca libros por contenido similar usando vectores de embeddings.
- **Categorización automática**: Clasifica libros automáticamente usando un modelo zero-shot.
- **Análisis de sentimientos**: Detecta el sentimiento dominante en el contenido de los libros.
- **Detección de duplicados**: Evita agregar libros con el mismo título.
- **Compatible con React Native**: Configurada para funcionar con aplicaciones móviles.

## Requisitos

- Python 3.8+
- Cuenta de Supabase con tabla `documents` configurada para vectores
- Clave API de OpenAI
- Opcionalmente: Clave API de Hugging Face

## Configuración

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/api-book.git
cd api-book
```

2. Instalar dependencias:
```bash
uv venv
uv pip install -r requirements.txt
```

3. Configurar variables de entorno (crear archivo `.env`):
```bash
cp .env.example .env
# Edita .env con tus claves
```

## Ejecución local

```bash
uvicorn main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Documentación de la API

La documentación interactiva estará disponible en `http://localhost:8000/docs`

## Endpoints principales

- `GET /search`: Busca libros por similitud semántica
- `POST /upload_book`: Sube un nuevo libro con embeddings
- `POST /classify_book`: Clasifica y analiza el sentimiento de un texto

## Despliegue

### Usando Docker

```bash
docker build -t api-book .
docker run -p 8000:8000 --env-file .env api-book
```

### Usando Docker Compose

```bash
docker-compose up -d
```

### Despliegue en servicios cloud

#### Render.com
Crea un nuevo servicio web y apunta al repositorio. Render detectará automáticamente el Dockerfile.

#### Railway.app
Conecta tu repositorio, Railway detectará el archivo requirements.txt.

## Conexión desde React Native

### Instalación de dependencias

```bash
npm install axios
# o
yarn add axios
```

### Ejemplo de uso

```javascript
import axios from 'axios';

const API_URL = 'https://tu-api-url.com'; // o 'http://localhost:8000' para desarrollo

// Función para buscar libros
const searchBooks = async (query, sentiment = null) => {
  try {
    let url = `${API_URL}/search?query=${encodeURIComponent(query)}`;
    if (sentiment) {
      url += `&dominant_sentiment=${encodeURIComponent(sentiment)}`;
    }
    
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error('Error al buscar libros:', error);
    throw error;
  }
};

// Función para clasificar un texto
const classifyText = async (content) => {
  try {
    const response = await axios.post(`${API_URL}/classify_book`, { content });
    return response.data;
  } catch (error) {
    console.error('Error al clasificar texto:', error);
    throw error;
  }
};

// Función para subir un libro
const uploadBook = async (content, metadata) => {
  try {
    const response = await axios.post(`${API_URL}/upload_book`, { 
      content, 
      metadata 
    });
    return response.data;
  } catch (error) {
    console.error('Error al subir libro:', error);
    throw error;
  }
};
```

## Pruebas

Para ejecutar las pruebas:

```bash
uv run pytest tests/
```

## Licencia

MIT
