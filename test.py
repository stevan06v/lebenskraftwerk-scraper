from vimeodlpy import downloader

if __name__ == "__main__":

    downloader.download(
        url="https://player.vimeo.com/video/949525438",
        output_path="output.mp4",
        referer="https://go.van-gerrevink.eu/coaching-programm-manufaktur",
    )