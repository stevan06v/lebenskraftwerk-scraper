import os
from concurrent.futures import ThreadPoolExecutor
import whisper
from pydub import AudioSegment
from docx import Document

COURSE_DIR = "/Volumes/Stevans-HDD/lebenskraftwerk_export/"
MEDIA_DIR = os.path.dirname(os.getcwd()) + "/out/media/"
WHISPER_MODEL = whisper.load_model("small")
MAX_WORKERS = 1


def convert_to_mp3(video_file_path: str):
    audio = AudioSegment.from_file(video_file_path, format="mp4")
    audio = audio.set_frame_rate(20000)
    audio.export(video_file_path.replace(".mp4", ".mp3"), format="mp3")


def mirror_directory_structure():
    for root, dirs, _ in os.walk(COURSE_DIR):
        rel_path = os.path.relpath(root, COURSE_DIR)
        target_path = os.path.join(MEDIA_DIR, rel_path)

        if not os.path.exists(target_path):
            os.makedirs(target_path)
            print(f"Created directory: {target_path}")


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def generate_transcript(audio_path: str, docx_output_path: str = None):
    result = WHISPER_MODEL.transcribe(audio=audio_path)
    transcript = result.get("text") if isinstance(result, dict) else str(result)

    ensure_dir(os.path.dirname(docx_output_path))

    document = Document()
    document.add_paragraph(transcript)
    document.save(docx_output_path)

    print(f"Transcript saved to: {docx_output_path}")

    os.remove(audio_path)

    return transcript


def process_videos():
    module_dirs = os.listdir(COURSE_DIR)
    tasks = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for iterator in module_dirs:
            iterator_dir = os.path.join(COURSE_DIR, iterator)

            if os.path.isdir(iterator_dir):
                videos = os.listdir(os.path.join(COURSE_DIR, iterator))
                for video in videos:
                    if video.endswith(".mp4"):
                        video_path = os.path.join(COURSE_DIR, iterator, video)
                        future = executor.submit(
                            process_single_video,
                            video_path,
                        )
                        tasks.append(future)


def process_single_video(video_path: str):
    convert_to_mp3(video_path)

    mp3_path = video_path.replace(".mp4", ".mp3")
    docx_output_path = (
        mp3_path
        .replace(".mp3", ".docx")
        .replace(COURSE_DIR, MEDIA_DIR)
    )

    print(f"Processing: {video_path}")
    print(f"→ mp3: {mp3_path}")
    print(f"→ docx output: {docx_output_path}")

    generate_transcript(mp3_path, docx_output_path)


if __name__ == "__main__":
    mirror_directory_structure()
    process_videos()
