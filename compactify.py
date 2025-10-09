import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from libs.models import Lesson
import os
import subprocess

DIRECTORY_NAME = "lebenskraftwerk_export"
MAX_FILE_NAME_LENGTH = 245
MAX_WORKERS = 8


def load_lessons_from_file(path: str) -> List[Lesson]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lessons = [Lesson(**item) for item in data]
    return lessons


def download_and_convert(lesson: Lesson, base_dir: str) -> str:
    module_dir = os.path.join(base_dir, lesson.module_title)
    os.makedirs(module_dir, exist_ok=True)

    safe_name = lesson.lesson_name.replace("/", "_").replace("\\", "_")
    short_safe_name = safe_name[:MAX_FILE_NAME_LENGTH]
    tmp_path = os.path.join(module_dir, f"{safe_name}_raw.mp4")
    out_path = os.path.join(module_dir, f"{safe_name}.mp4")

    print(f"Downloading {lesson.lesson_id} → {tmp_path}")
    subprocess.run([
        "streamlink",
        lesson.video_url,
        "best",
        "-o", tmp_path
    ], check=True)

    print(f"Converting {tmp_path} → {out_path}")
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", tmp_path,
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        out_path
    ], check=True)

    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return out_path


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
    seen_courses = set()
    for lesson in lessons:
        if lesson.module_title not in seen_courses:
            seen_courses.add(lesson.module_title)
            try:
                os.mkdir(f"{DIRECTORY_NAME}/{lesson.module_title}")
                print(f"Directory '{DIRECTORY_NAME}/{lesson.module_title}' created successfully.")
            except FileExistsError:
                print(f"Directory '{DIRECTORY_NAME}/{lesson.module_title}' already exists.")
            except PermissionError:
                print(f"Permission denied: Unable to create '{DIRECTORY_NAME}/{lesson.module_title}'.")
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == "__main__":
    try:
        loaded_lessons = load_lessons_from_file('lessons.json')
        for lesson in loaded_lessons:
            print(lesson)

        os.mkdir(DIRECTORY_NAME)
        print(f"Directory '{DIRECTORY_NAME}' created successfully.")
        create_distinct_directories(loaded_lessons)

        download_lessons_parallel(loaded_lessons, max_workers=MAX_WORKERS)

        print(
            f"All lessons downloaded successfully. Output files are located in '{DIRECTORY_NAME}'."
        )

    except FileExistsError:
        print(f"Directory '{DIRECTORY_NAME}' already exists.")
    except PermissionError:
        print(f"Permission denied: Unable to create '{DIRECTORY_NAME}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
