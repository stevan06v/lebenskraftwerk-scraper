# Gruppiere nach Modul-Titel
import os
from collections import defaultdict
from compactify import load_lessons_from_file


lessons = load_lessons_from_file("../lessons.json")

modules = defaultdict(list)
for lesson in lessons:
    modules[lesson.module_title].append(lesson)

markdown_datei = "lektionen.md"

zeilen = ["# Kursübersicht\n"]

for modul_titel, lektionen in modules.items():
    zeilen.append(f"## Modul: {modul_titel}\n")

    for lesson in lektionen:
        safe_name = lesson.lesson_name.replace("/", "_").replace("\\", "_")
        ausgabe_pfad = f"lebenskraftwerk_export/{modul_titel}/{safe_name}.mp4"

        zeilen.append(f"### Video: {lesson.lesson_name}")
        zeilen.append(f"- **Video-ID:** {lesson.lesson_id}")
        zeilen.append(f"- **Video-Titel:** {lesson.video_title}")
        zeilen.append(f"- **Video-URL:** [{lesson.video_url}]({lesson.video_url})")
        zeilen.append(f"- **Ausgabepfad:** `{ausgabe_pfad}`")
        zeilen.append("")

with open(markdown_datei, "w", encoding="utf-8") as f:
    f.write("\n".join(zeilen))

print(f"Markdown-Datei wurde erstellt: {markdown_datei}")