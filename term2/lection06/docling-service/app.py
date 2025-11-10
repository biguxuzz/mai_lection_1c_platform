"""
Docling Document Processing Service

Сервис для обработки документов различных форматов (PDF, DOCX, PPTX, Images, etc.)
с использованием Docling и разбивкой на чанки для RAG системы.
"""

import logging
import os
import tempfile
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import requests

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
)
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling_core.types.doc import PictureItem

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "docling_uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER = Path(tempfile.gettempdir()) / "docling_output"
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'pptx', 'ppt', 
    'png', 'jpg', 'jpeg', 'gif', 'bmp',
    'html', 'htm', 'md', 'txt', 'csv',
    'asciidoc', 'adoc'
}

# Конфигурация для LM Studio (для описания изображений)
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1/chat/completions")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "smolvlm-256m-instruct")
LM_STUDIO_TIMEOUT = int(os.getenv("LM_STUDIO_TIMEOUT", "90"))

# Конфигурация для RAG сервиса
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8000/ingest")

# Параметры чанкинга
CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "128"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "30"))


def allowed_file(filename: str) -> bool:
    """Проверка разрешенного расширения файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def make_json_serializable(obj: Any) -> Any:
    """
    Рекурсивно преобразует объект в JSON-сериализуемый формат.
    Конвертирует методы, классы и другие несериализуемые типы в строки или простые типы.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    if callable(obj):
        # Если это метод или функция - возвращаем None или пытаемся вызвать
        try:
            result = obj()
            return make_json_serializable(result)
        except:
            return None
    
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    
    # Для других типов пытаемся преобразовать в строку
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def get_lm_studio_options() -> PictureDescriptionApiOptions:
    """
    Конфигурация для LM Studio API для описания изображений в документах.
    
    Returns:
        PictureDescriptionApiOptions: Настройки для описания изображений
    """
    options = PictureDescriptionApiOptions(
        url=LM_STUDIO_URL,
        params=dict(
            model=LM_STUDIO_MODEL,
            seed=42,
            max_completion_tokens=150,
            temperature=0.1,  # Низкая температура для минимизации галлюцинаций
        ),
        prompt=(
            "What do you see in this image? "
            "Describe only what is visible: forms, tables, buttons, text fields, or charts."
        ),
        timeout=LM_STUDIO_TIMEOUT,
    )
    return options


def create_document_converter(enable_image_description: bool = True) -> DocumentConverter:
    """
    Создание конвертера документов с настройками.
    
    Args:
        enable_image_description: Включить описание изображений через LM Studio
        
    Returns:
        DocumentConverter: Настроенный конвертер документов
    """
    # Настройки для PDF pipeline
    pipeline_options = PdfPipelineOptions()
    
    if enable_image_description:
        try:
            pipeline_options.enable_remote_services = True
            pipeline_options.do_picture_description = True
            pipeline_options.picture_description_options = get_lm_studio_options()
            pipeline_options.images_scale = 2.0  # Улучшенное качество изображений
            pipeline_options.generate_picture_images = True  # Генерация изображений
            logger.info(f"Image description enabled via LM Studio: {LM_STUDIO_URL}")
        except Exception as e:
            logger.warning(f"Failed to enable image description: {e}. Continuing without it.")
            enable_image_description = False
    
    # Создание конвертера с поддержкой всех основных форматов
    doc_converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.PPTX,
            InputFormat.ASCIIDOC,
            InputFormat.CSV,
            InputFormat.MD,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=StandardPdfPipeline,
                backend=PyPdfiumDocumentBackend,
                pipeline_options=pipeline_options if enable_image_description else None
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline,
                pipeline_options=pipeline_options if enable_image_description else None  # Добавляем VLM для DOCX!
            ),
        },
    )
    
    return doc_converter


def chunk_markdown_text(text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Разбивка markdown текста на чанки с учетом токенов.
    
    Args:
        text: Markdown текст для разбивки
        metadata: Метаданные документа
        
    Returns:
        List[Dict]: Список чанков с метаданными
    """
    try:
        import tiktoken
        
        # Используем tiktoken для подсчета токенов (как в GPT)
        encoding = tiktoken.get_encoding("cl100k_base")
        
        chunks = []
        lines = text.split('\n')
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for line in lines:
            line_tokens = len(encoding.encode(line))
            
            # Если добавление строки превысит лимит, сохраняем текущий чанк
            if current_tokens + line_tokens > CHUNK_SIZE_TOKENS and current_chunk:
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_index': chunk_index,
                        'chunk_tokens': current_tokens,
                        'total_chunks': None,  # Заполним позже
                    }
                })
                
                # Начинаем новый чанк с overlap
                overlap_lines = []
                overlap_tokens = 0
                
                for overlap_line in reversed(current_chunk):
                    overlap_line_tokens = len(encoding.encode(overlap_line))
                    if overlap_tokens + overlap_line_tokens <= CHUNK_OVERLAP_TOKENS:
                        overlap_lines.insert(0, overlap_line)
                        overlap_tokens += overlap_line_tokens
                    else:
                        break
                
                current_chunk = overlap_lines
                current_tokens = overlap_tokens
                chunk_index += 1
            
            current_chunk.append(line)
            current_tokens += line_tokens
        
        # Добавляем последний чанк
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'content': chunk_text,
                'metadata': {
                    **metadata,
                    'chunk_index': chunk_index,
                    'chunk_tokens': current_tokens,
                    'total_chunks': None,
                }
            })
        
        # Обновляем total_chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = total_chunks
        
        logger.info(f"Created {total_chunks} chunks from document")
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking text: {e}")
        # Fallback: возвращаем весь текст как один чанк
        return [{
            'content': text,
            'metadata': {
                **metadata,
                'chunk_index': 0,
                'total_chunks': 1,
                'chunking_error': str(e)
            }
        }]


def process_document(file_path: Path, original_filename: str, enable_image_description: bool = True) -> Dict[str, Any]:
    """
    Обработка документа через Docling.
    
    Args:
        file_path: Путь к файлу для обработки
        original_filename: Оригинальное имя файла
        enable_image_description: Включить описание изображений
        
    Returns:
        Dict: Результат обработки с markdown и метаданными
    """
    try:
        logger.info(f"Processing document: {original_filename}")
        
        # Создание конвертера
        doc_converter = create_document_converter(enable_image_description)
        
        # Конвертация документа
        result = doc_converter.convert(file_path)
        
        # Извлечение markdown
        markdown_text = result.document.export_to_markdown()
        
        # Извлечение информации об изображениях
        pictures_info = []
        for element, _level in result.document.iterate_items():
            if isinstance(element, PictureItem):
                # Безопасное получение caption
                try:
                    caption = element.caption_text(doc=result.document)
                except:
                    caption = str(element.caption) if hasattr(element, 'caption') else None
                
                # Безопасное получение annotations
                annotations = []
                if hasattr(element, 'annotations'):
                    try:
                        # Если annotations - это список объектов, преобразуем их в словари
                        if isinstance(element.annotations, list):
                            annotations = [str(ann) for ann in element.annotations]
                        else:
                            annotations = str(element.annotations)
                    except:
                        annotations = []
                
                picture_data = {
                    'self_ref': str(element.self_ref),
                    'caption': caption,
                    'annotations': annotations
                }
                pictures_info.append(picture_data)
        
        logger.info(f"Document processed successfully. Found {len(pictures_info)} images.")
        
        # Безопасное получение количества страниц
        num_pages = None
        if hasattr(result.document, 'num_pages'):
            num_pages_attr = getattr(result.document, 'num_pages')
            if callable(num_pages_attr):
                try:
                    num_pages = num_pages_attr()
                except:
                    num_pages = None
            else:
                num_pages = num_pages_attr
        
        return {
            'success': True,
            'markdown': markdown_text,
            'pictures': pictures_info,
            'metadata': {
                'filename': original_filename,
                'format': result.input.format.value if hasattr(result.input, 'format') else 'unknown',
                'pages': num_pages,
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing document {original_filename}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'filename': original_filename
        }


def send_chunks_to_rag(chunks: List[Dict[str, Any]], document_id: str) -> Dict[str, Any]:
    """
    Отправка чанков в RAG сервис.
    
    Args:
        chunks: Список чанков для отправки
        document_id: Уникальный идентификатор документа
        
    Returns:
        Dict: Результат отправки
    """
    results = {
        'document_id': document_id,
        'total_chunks': len(chunks),
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for i, chunk in enumerate(chunks):
        try:
            response = requests.post(
                RAG_SERVICE_URL,
                json={
                    'content': chunk['content'],
                    'metadata': {
                        **chunk['metadata'],
                        'document_id': document_id,
                        'processed_by': 'docling-service',
                        'processed_at': datetime.utcnow().isoformat()
                    }
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                results['successful'] += 1
                logger.info(f"Chunk {i+1}/{len(chunks)} sent successfully to RAG")
            else:
                results['failed'] += 1
                error_msg = f"Chunk {i+1}: HTTP {response.status_code}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
        except Exception as e:
            results['failed'] += 1
            error_msg = f"Chunk {i+1}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"Error sending chunk {i+1} to RAG: {e}")
    
    return results


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса."""
    return jsonify({
        'status': 'healthy',
        'service': 'docling-service',
        'lm_studio_url': LM_STUDIO_URL,
        'rag_service_url': RAG_SERVICE_URL
    })


@app.route('/process', methods=['POST'])
def process_document_endpoint():
    """
    Endpoint для обработки документа.
    
    Принимает файл через multipart/form-data или JSON с URL/base64.
    Параметры:
    - file: файл документа (multipart)
    - enable_image_description: включить описание изображений (bool, default: true)
    - send_to_rag: отправить чанки в RAG автоматически (bool, default: true)
    - metadata: дополнительные метаданные (JSON object)
    
    Returns:
        JSON с результатами обработки и чанками
    """
    try:
        # Проверка наличия файла
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Получение параметров
        enable_image_description = request.form.get('enable_image_description', 'true').lower() == 'true'
        send_to_rag = request.form.get('send_to_rag', 'true').lower() == 'true'
        
        # Дополнительные метаданные
        metadata = {}
        if 'metadata' in request.form:
            try:
                metadata = json.loads(request.form['metadata'])
            except:
                logger.warning("Failed to parse metadata JSON")
        
        # Сохранение файла
        filename = secure_filename(file.filename)
        document_id = str(uuid.uuid4())
        file_path = UPLOAD_FOLDER / f"{document_id}_{filename}"
        file.save(file_path)
        
        logger.info(f"File saved: {file_path}")
        
        try:
            # Обработка документа
            process_result = process_document(
                file_path,
                filename,
                enable_image_description
            )
            
            if not process_result['success']:
                return jsonify(process_result), 500
            
            # Подготовка метаданных для чанков
            chunk_metadata = {
                **metadata,
                'source_filename': filename,
                'document_id': document_id,
                'format': process_result['metadata'].get('format'),
                'pages': process_result['metadata'].get('pages'),
                'has_pictures': len(process_result['pictures']) > 0,
                'pictures_count': len(process_result['pictures']),
            }
            
            # Разбивка на чанки
            chunks = chunk_markdown_text(
                process_result['markdown'],
                chunk_metadata
            )
            
            response_data = {
                'success': True,
                'document_id': document_id,
                'filename': filename,
                'metadata': process_result['metadata'],
                'pictures': process_result['pictures'],
                'chunks_count': len(chunks),
                'chunks': chunks,  # Возвращаем ВСЕ чанки
                'chunks_preview_only': False
            }
            
            # Отправка в RAG, если требуется
            if send_to_rag:
                rag_result = send_chunks_to_rag(chunks, document_id)
                response_data['rag_ingestion'] = rag_result
            
            # Очищаем данные от несериализуемых объектов
            response_data = make_json_serializable(response_data)
            
            return jsonify(response_data), 200
            
        finally:
            # Удаление временного файла
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Temporary file deleted: {file_path}")
            
    except Exception as e:
        logger.error(f"Error in process endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/formats', methods=['GET'])
def get_supported_formats():
    """Получение списка поддерживаемых форматов."""
    return jsonify({
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'image_description_available': True,
        'chunking_enabled': True,
        'chunk_size_tokens': CHUNK_SIZE_TOKENS,
        'chunk_overlap_tokens': CHUNK_OVERLAP_TOKENS
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=False)


