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


def load_lessons_from_file(path: str) -> List[Lesson]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lessons = [Lesson(**item) for item in data]
    return lessons


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
    except Exception as e:
        print(f"Failed to download {lesson.lesson_id}: {e}")
        time.sleep(10)
        return download_and_convert(lesson, DIRECTORY_NAME)

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

    except FileExistsError:
        print(f"Directory '{DIRECTORY_NAME}' already exists.")
    except PermissionError:
        print(f"Permission denied: Unable to create '{DIRECTORY_NAME}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
