import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from libs.models import Lesson
import os
from vimeodlpy import downloader

DIRECTORY_NAME = "lebenskraftwerk_export"
MAX_FILE_NAME_LENGTH = 245
MAX_WORKERS = 10

success = set()
failed = set()

FAILED_FILE = "failed.json"


def load_lessons_from_file(path: str) -> List[Lesson]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lessons = [Lesson(**item) for item in data]
    return lessons


def load_failed_lessons() -> List[Lesson]:
    if not os.path.exists(FAILED_FILE):
        return []
    try:
        with open(FAILED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        failed_lessons = [Lesson(**item) for item in data]
        return failed_lessons
    except Exception as e:
        print(f"Error loading {FAILED_FILE}: {e}")
        return []


def save_failed_lessons(lessons: List[Lesson]):
    serializable = []
    for lesson in lessons:
        if hasattr(lesson, "model_dump"):
            d = lesson.model_dump()
        elif hasattr(lesson, "dict"):
            d = lesson.dict()
        else:
            d = lesson.__dict__
        serializable.append(d)

    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def append_failed_lesson(lesson: Lesson):
    fails = load_failed_lessons()
    existing_ids = {l.lesson_id for l in fails}
    if lesson.lesson_id in existing_ids:
        return
    fails.append(lesson)
    save_failed_lessons(fails)


def remove_failed_lesson(lesson_id: str):
    fails = load_failed_lessons()
    new = [l for l in fails if l.lesson_id != lesson_id]
    if len(new) != len(fails):
        save_failed_lessons(new)


def download_and_convert(lesson: Lesson, base_dir: str):
    module_dir = os.path.join(base_dir, lesson.module_title)
    os.makedirs(module_dir, exist_ok=True)

    safe_name = lesson.lesson_name.replace("/", "_").replace("\\", "_")
    out_path = os.path.join(module_dir, f"{safe_name}.mp4")

    print(f"Downloading {lesson.lesson_id} → {out_path}")

    try:
        downloader.download(
            url=lesson.video_url,
            output_path=out_path,
            referer=None,
        )
        success.add(lesson.lesson_id)
        # If it was previously failed, remove it
        remove_failed_lesson(lesson.lesson_id)
    except Exception as e:
        print(f"Failed to download {lesson.lesson_id}: {e}")
        failed.add(lesson.lesson_id)
        append_failed_lesson(lesson)

    return lesson.lesson_id, out_path


def download_lessons_parallel(lessons: List[Lesson], max_workers: int = 4):
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_lesson = {
            executor.submit(download_and_convert, lesson, DIRECTORY_NAME): lesson
            for lesson in lessons
        }
        for future in as_completed(future_to_lesson):
            lesson = future_to_lesson[future]
            try:
                lesson_id, out_path = future.result()
                print(f"Downloaded {lesson_id}")
                results[lesson_id] = out_path
            except Exception as e:
                print(f"Failed {lesson.lesson_id}: {e}")
    return results


def retry_failed(max_retries: int = 3, delay_secs: float = 5.0):
    for attempt in range(1, max_retries + 1):
        fails = load_failed_lessons()
        if not fails:
            print("No failed lessons to retry.")
            return
        print(f"[Retry {attempt}/{max_retries}] Retrying {len(fails)} failed lessons.")
        for entry in fails.copy():
            lesson = Lesson(
                module_title=entry.module_title,
                lesson_id=entry.lesson_id,
                lesson_name=entry.lesson_name,
                video_url=entry.video_url,
                video_title=entry.video_title,
            )
            download_and_convert(lesson, DIRECTORY_NAME)
        time.sleep(delay_secs)

    remains = load_failed_lessons()
    if remains:
        print("After retries, these lessons still failed:")
        for e in remains:
            print(f" - {e['lesson_id']} : {e['lesson_name']}")


def create_distinct_directories(lessons: List[Lesson]):
    seen = set()
    for lesson in lessons:
        if lesson.module_title not in seen:
            seen.add(lesson.module_title)
            dirpath = os.path.join(DIRECTORY_NAME, lesson.module_title)
            try:
                os.makedirs(dirpath, exist_ok=True)
                print(f"Directory '{dirpath}' created.")
            except Exception as e:
                print(f"Could not create '{dirpath}': {e}")


if __name__ == "__main__":
    try:
        loaded_lessons = load_lessons_from_file('remaining.json')
        for lesson in loaded_lessons:
            print(lesson)

        os.makedirs(DIRECTORY_NAME, exist_ok=False)
        print(f"Directory '{DIRECTORY_NAME}' created successfully.")
        create_distinct_directories(loaded_lessons)

        download_lessons_parallel(loaded_lessons, max_workers=MAX_WORKERS)

        retry_failed(max_retries=25, delay_secs=300.0)

        print(f"Download process complete. Check '{FAILED_FILE}' for any remaining failures.")

        if not load_failed_lessons():
            try:
                os.remove(FAILED_FILE)
            except OSError:
                pass

    except FileExistsError:
        print(f"Directory '{DIRECTORY_NAME}' already exists.")
    except PermissionError:
        print(f"Permission denied: Unable to create '{DIRECTORY_NAME}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
