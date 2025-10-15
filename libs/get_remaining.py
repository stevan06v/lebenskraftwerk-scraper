import json
import os
from pathlib import Path
from typing import List

from libs.models import Lesson

FAILED_FILE = "../lessons.json"
DIRECTORY_NAME = "/Volumes/Stevans-HDD/lebenskraftwerk_export"
REMAINING_FILE = "../remaining.json"


def load_remaining_lessons() -> List[Lesson]:
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


def make_safe_filename(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").strip()


def save_remaininglessons(lessons: List[Lesson]):
    serializable = []
    for lesson in lessons:
        if hasattr(lesson, "model_dump"):
            d = lesson.model_dump()
        elif hasattr(lesson, "dict"):
            d = lesson.dict()
        else:
            d = lesson.__dict__
        serializable.append(d)

    with open(REMAINING_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def get_remaining():
    lessons = load_remaining_lessons()
    if not lessons:
        print("No lessons found.")
        exit(0)

    downloaded_videos = []

    base_path = Path(DIRECTORY_NAME)
    for module_dir in base_path.iterdir():
        if module_dir.is_dir():
            mp4_files = [f.name for f in module_dir.glob("*.mp4")]
            downloaded_videos.extend(mp4_files)

    downloaded_titles = {
        f.replace(".mp4", "").strip() for f in downloaded_videos
    }

    not_downloaded = [
        lesson for lesson in lessons
        if make_safe_filename(lesson.lesson_name) not in downloaded_titles
    ]

    print(f"Already downloaded: {len(downloaded_titles)}")
    print(f"Remaining lessons: {len(not_downloaded)}\n")

    for lesson in not_downloaded:
        print(f"[MISSING] {lesson.module_title} → {lesson.lesson_name}")
    print(len(not_downloaded))

    save_remaininglessons(not_downloaded)

if __name__ == "__main__":
    get_remaining()
