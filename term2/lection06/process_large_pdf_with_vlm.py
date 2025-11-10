"""
Обработка большого PDF с VLM описанием картинок
Специально для файлов размером 100+ MB
"""

import requests
import json
import sys
from pathlib import Path
import time

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def process_large_pdf(pdf_path: str):
    """Обработка большого PDF файла с VLM"""
    
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"[ОШИБКА] Файл не найден: {pdf_path}")
        return None
    
    print("\n" + "="*80)
    print("ОБРАБОТКА БОЛЬШОГО PDF С VLM")
    print("="*80)
    print(f"\nФайл: {pdf_file.name}")
    print(f"Размер: {pdf_file.stat().st_size / (1024*1024):.2f} MB")
    
    url = "http://localhost:8001/process"
    
    print("\n⚠ ВНИМАНИЕ:")
    print("  - Файл большой (178 MB)")
    print("  - С VLM обработка займет 1-2 часа")
    print("  - Будут описаны ВСЕ изображения в книге")
    print("  - Не закрывайте терминал!")
    
    print("\nОтправка запроса...")
    print("Начало обработки:", time.strftime("%H:%M:%S"))
    
    with open(pdf_file, 'rb') as f:
        files = {'file': (pdf_file.name, f, 'application/pdf')}
        data = {
            'enable_image_description': 'true',  # VLM включен!
            'send_to_rag': 'true',  # Автоматически отправляем в RAG!
            'metadata': json.dumps({
                'source': 'djvu_converter',
                'original_format': 'djvu',
                'category': '1C_technical_documentation',
                'book_title': 'Настольная книга 1С эксперта',
                'author': 'unknown',
                'language': 'russian'
            })
        }
        
        try:
            # Таймаут 3 часа (10800 секунд) - на всякий случай
            print("\nЗапрос отправлен. Ожидание ответа...")
            print("(Это займет 1-2 часа, терпение!)")
            
            start_time = time.time()
            
            response = requests.post(
                url, 
                files=files, 
                data=data, 
                timeout=10800,  # 3 часа
                stream=False
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n" + "="*80)
                print("УСПЕХ! ОБРАБОТКА ЗАВЕРШЕНА")
                print("="*80)
                print(f"Время обработки: {duration/60:.1f} минут ({duration:.0f} секунд)")
                print(f"Окончание: {time.strftime('%H:%M:%S')}")
                
                # Сохранение результатов
                output_dir = Path("lection06/example/converted_md")
                output_dir.mkdir(exist_ok=True, parents=True)
                
                base_name = "Настольная_книга_1С_эксперта"
                
                # JSON с полными результатами
                json_path = output_dir / f"{base_name}_full_result.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n✓ JSON сохранен: {json_path}")
                print(f"  Размер: {json_path.stat().st_size / (1024*1024):.2f} MB")
                
                # Markdown из всех чанков
                if 'chunks' in result and result['chunks']:
                    all_content = []
                    for chunk in result['chunks']:
                        all_content.append(chunk['content'])
                    
                    markdown_text = '\n\n'.join(all_content)
                    
                    md_path = output_dir / f"{base_name}.md"
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_text)
                    print(f"✓ Markdown сохранен: {md_path}")
                    print(f"  Размер: {len(markdown_text) / 1024:.1f} KB")
                
                # Статистика
                print("\n" + "="*80)
                print("СТАТИСТИКА")
                print("="*80)
                print(f"Документ ID: {result.get('document_id')}")
                print(f"Чанков создано: {result.get('chunks_count')}")
                print(f"Изображений всего: {len(result.get('pictures', []))}")
                
                pictures_with_desc = sum(1 for p in result.get('pictures', []) 
                                        if p.get('annotations') or p.get('caption'))
                print(f"Изображений с описаниями VLM: {pictures_with_desc}")
                
                if pictures_with_desc > 0:
                    print(f"\n✓ VLM описание работает! {pictures_with_desc} картинок описаны")
                
                # Примеры описаний
                if pictures_with_desc > 0:
                    print("\n" + "="*80)
                    print("ПРИМЕРЫ ОПИСАНИЙ ИЗОБРАЖЕНИЙ")
                    print("="*80)
                    
                    shown = 0
                    for i, pic in enumerate(result.get('pictures', []), 1):
                        if shown >= 5:
                            break
                        
                        annotations = pic.get('annotations', [])
                        caption = pic.get('caption', '')
                        
                        if annotations or caption:
                            print(f"\nИзображение #{i}:")
                            if caption:
                                print(f"  Caption: {caption[:100]}...")
                            if annotations:
                                ann_text = str(annotations[0]) if annotations else ''
                                # Извлекаем text= из аннотации
                                if 'text=' in ann_text:
                                    start = ann_text.find("text='") + 6
                                    end = ann_text.find("'", start)
                                    if end > start:
                                        desc = ann_text[start:end]
                                        print(f"  Описание: {desc[:150]}...")
                            shown += 1
                
                print("\n" + "="*80)
                print("✅ КОНВЕРТАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
                print("="*80)
                print(f"\nРезультаты: {output_dir}")
                
                return result
                
            else:
                print(f"\n[ОШИБКА] HTTP {response.status_code}")
                print(f"Ответ: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            print("\n[TIMEOUT] Превышено время ожидания (3 часа)")
            print("Файл слишком большой или LM Studio не отвечает")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"\n[ОШИБКА СОЕДИНЕНИЯ] {e}")
            print("\nВозможные причины:")
            print("  1. Docling-service упал из-за нехватки памяти")
            print("  2. Проверьте логи: docker logs lection6_docling_service")
            print("  3. Увеличьте память Docker (Settings → Resources)")
            return None
        except Exception as e:
            print(f"\n[ОШИБКА] {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python process_large_pdf_with_vlm.py <путь_к_pdf>")
        print("\nПример:")
        print('  python process_large_pdf_with_vlm.py "C:\\Temp\\book.pdf"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("\n" + "="*80)
    print("ОБРАБОТКА БОЛЬШОГО PDF С VLM ОПИСАНИЕМ КАРТИНОК")
    print("="*80)
    
    result = process_large_pdf(pdf_path)
    
    if result:
        print("\n✅ Все готово! Можете использовать результаты.")
    else:
        print("\n✗ Обработка завершена с ошибками")

