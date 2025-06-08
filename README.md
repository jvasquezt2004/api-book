# API de Libros

API para gestionar y buscar libros con categorización automática y análisis de sentimientos utilizando FastAPI, Supabase y modelos de IA.

## Características

- **Búsqueda semántica**: Busca libros por contenido similar usando vectores de embeddings.
- **Categorización automática**: Clasifica libros automáticamente usando un modelo zero-shot.
- **Análisis de sentimientos**: Detecta el sentimiento dominante en el contenido de los libros.
- **Detección de duplicados**: Evita agregar libros con el mismo título.
- **Compatible con Expo Go y React Native**: Configurada para funcionar con aplicaciones móviles.

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

## Documentación de Rutas API

A continuación se detallan todas las rutas disponibles en la API y cómo utilizarlas.

### 1. Ruta Raíz (`GET /`)

**Descripción**: Verifica que la API está funcionando.

**Respuesta**:
```json
{
  "message": "Fast API with Supabase Vector Store"
}
```

### 2. Búsqueda de Libros (`GET /search`)

**Descripción**: Busca libros usando similitud semántica basada en embeddings.

**Parámetros**:
- `query` (string): Texto de búsqueda (requerido)
- `dominant_sentiment` (string, opcional): Filtro de sentimiento ("joy", "fear", "neutral")
- `page` (int, opcional): Número de página (comienza en 1, por defecto: 1)
- `size` (int, opcional): Tamaño de página (por defecto: 10)

**Respuesta**:
```json
{
  "results": [
    {
      "document_id": "uuid-string",
      "content": "Contenido truncado del libro...",
      "metadata": {
        "title": "Título del libro",
        "author": "Autor del libro",
        "dominant_sentiment": "joy",
        "category": "Fiction"
      },
      "score": 0.89
    }
  ],
  "total": 42,
  "page": 1,
  "size": 10,
  "pages": 5
}
```

### 3. Subida de Libros (`POST /upload_book`)

**Descripción**: Sube un nuevo libro a la base de datos, generando embeddings automáticamente.

**Cuerpo de la Solicitud**:
```json
{
  "content": "Contenido completo del libro...",
  "metadata": {
    "title": "Título del libro",
    "author": "Autor del libro",
    "year": 2023,
    "dominant_sentiment": "joy",
    "category": "Fiction"
  },
  "embeddings": null
}
```

**Respuesta (éxito)**:
```json
{
  "document_id": "uuid-string",
  "message": "Book uploaded successfully"
}
```

**Respuesta (error: duplicado)**:
```json
{
  "error": "Book with title 'Título del libro' already exists"
}
```

### 4. Clasificación de Libros (`POST /classify_book`)

**Descripción**: Analiza contenido para determinar categoría y sentimiento dominante.

**Cuerpo de la Solicitud**:
```json
{
  "content": "Contenido del libro a clasificar...",
  "category": null,
  "dominant_sentiment": null
}
```

**Respuesta**:
```json
{
  "truncated_content": "Primeros 100 caracteres...",
  "category": "Fiction",
  "category_score": 0.92,
  "dominant_sentiment": "joy",
  "sentiment_score": 0.75,
  "model_source": "huggingface_api"
}
```

### 5. Obtener Resumen (`GET /get_summary`)

**Descripción**: Genera un resumen de un artículo de Wikipedia.

**Parámetros**:
- `topic` (string): Tema sobre el cual generar el resumen (requerido)

**Respuesta**:
```json
{
  "summary": "Resumen generado sobre el tema..."
}
```

## Conexión desde Expo Go

### Instalación de dependencias

```bash
npx expo install axios
```

### Ejemplo de uso con Expo

```javascript
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TextInput, Button, StyleSheet } from 'react-native';
import axios from 'axios';
import Constants from 'expo-constants';

// Configuración para usar IP local si estás en desarrollo
const isDevelopment = process.env.NODE_ENV === 'development';
const API_URL = isDevelopment 
  ? 'http://192.168.1.XX:8000' // Reemplaza con tu IP local
  : 'https://tu-api-url.com';

export default function BookSearchScreen() {
  const [query, setQuery] = useState('');
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Función para buscar libros
  const searchBooks = async (searchQuery, sentiment = null, page = 1, size = 10) => {
    try {
      setLoading(true);
      setError(null);
      
      let url = `${API_URL}/search?query=${encodeURIComponent(searchQuery)}&page=${page}&size=${size}`;
      
      if (sentiment) {
        url += `&dominant_sentiment=${encodeURIComponent(sentiment)}`;
      }
      
      const response = await axios.get(url);
      setBooks(response.data.results);
      return response.data;
    } catch (error) {
      console.error('Error al buscar libros:', error);
      setError('No pudimos cargar los libros. Por favor intenta más tarde.');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Función para clasificar un texto
  const classifyBookContent = async (content, category = null, dominant_sentiment = null) => {
    try {
      const response = await axios.post(`${API_URL}/classify_book`, {
        content,
        category,
        dominant_sentiment
      });
      
      return response.data;
    } catch (error) {
      console.error('Error al clasificar el libro:', error);
      throw error;
    }
  };

  // Función para subir un libro
  const uploadBook = async (content, metadata) => {
    try {
      const response = await axios.post(`${API_URL}/upload_book`, { 
        content, 
        metadata,
        embeddings: null // Se generarán automáticamente
      });
      
      return response.data;
    } catch (error) {
      console.error('Error al subir libro:', error);
      throw error;
    }
  };

  // Ejemplo de flujo: clasificar y luego subir
  const classifyAndUploadBook = async (content, basicMetadata) => {
    try {
      // Primero clasificamos el contenido
      const classificationResult = await classifyBookContent(content);
      
      // Luego subimos con los metadatos enriquecidos
      const enrichedMetadata = {
        ...basicMetadata,
        category: classificationResult.category,
        dominant_sentiment: classificationResult.dominant_sentiment
      };
      
      return await uploadBook(content, enrichedMetadata);
    } catch (error) {
      console.error('Error en el proceso de clasificación y subida:', error);
      throw error;
    }
  };

  // Efecto para cargar libros iniciales
  useEffect(() => {
    if (query.length > 2) {
      const delaySearch = setTimeout(() => {
        searchBooks(query);
      }, 500);
      
      return () => clearTimeout(delaySearch);
    }
  }, [query]);

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.searchInput}
        placeholder="Buscar libros..."
        value={query}
        onChangeText={setQuery}
      />
      
      {loading && <Text>Cargando...</Text>}
      {error && <Text style={styles.errorText}>{error}</Text>}
      
      <FlatList
        data={books}
        keyExtractor={(item) => item.document_id}
        renderItem={({ item }) => (
          <View style={styles.bookItem}>
            <Text style={styles.bookTitle}>{item.metadata.title}</Text>
            <Text>Autor: {item.metadata.author}</Text>
            <Text>Categoría: {item.metadata.category}</Text>
            <Text>Sentimiento: {item.metadata.dominant_sentiment}</Text>
            <Text numberOfLines={2}>{item.content}</Text>
          </View>
        )}
      />
      
      {/* Otros componentes y funciones */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    marginTop: Constants.statusBarHeight,
  },
  searchInput: {
    height: 40,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    marginBottom: 16,
    paddingHorizontal: 8,
  },
  bookItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  bookTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  errorText: {
    color: 'red',
  }
});
```

### Consideraciones especiales para Expo Go

1. **Conexión en desarrollo**: Cuando trabajes con Expo Go y la API en tu máquina local, necesitas usar la IP de tu máquina en lugar de localhost porque la app corre en un dispositivo físico o emulador.

2. **CORS para Expo**: La API ya está configurada para aceptar solicitudes desde Expo en desarrollo.

3. **Manejo de errores específicos**:
```javascript
const handleApiError = (error) => {
  if (error.response) {
    // El servidor respondió con un código de error
    console.log(error.response.data);
    console.log(error.response.status);
    
    if (error.response.status === 429) {
      return "Demasiadas solicitudes. Por favor intenta más tarde.";
    }
    
    return error.response.data.error || "Error en el servidor";
  } else if (error.request) {
    // La solicitud fue realizada pero no recibimos respuesta
    console.log(error.request);
    return "No hay respuesta del servidor. Verifica tu conexión.";
  } else {
    // Error al configurar la solicitud
    console.log('Error', error.message);
    return "Error al realizar la solicitud.";
  }
};
```

### Flujo de Trabajo Recomendado

1. **Clasificación antes de subida**:
   - Primero clasifica el contenido para obtener metadatos enriquecidos
   - Luego sube el libro con toda la información

2. **Búsqueda con filtros**:
   - Implementa filtros por sentimiento para experiencia personalizada
   - Usa la paginación para cargar resultados bajo demanda
```

## Pruebas

Para ejecutar las pruebas:

```bash
uv run pytest tests/
```

## Licencia

MIT
