from pydantic import BaseModel


class Lesson(BaseModel):
    module_title: str
    lesson_id: str
    lesson_name: str
    video_url: str
    video_title: str

    def __str__(self) -> str:
        return (f"Lesson(id={self.lesson_id}, "
                f"module={self.module_title!r}, "
                f"title={self.lesson_name!r})")

    def __repr__(self) -> str:
        return self.__str__()
