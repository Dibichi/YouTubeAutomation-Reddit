
from Reddit import reddit
from Graphics.screenshot import get_thread_title
import config
from TextToSpeech.tts import create_tts, get_length
from pathlib import Path
from utils.clean_text import markdown_to_text
from utils.add_mp3_pause import add_pause
from VideoEditor.videomaker import make_final_video, make_subtitled_video
import math
import subprocess
import time
import OpenAI.chat_gpt as chat_gpt

RESPONSE_LENGTH = 170
ASK_REDDIT_PROMPT = f"Answer the question as a Reddit commenter in {RESPONSE_LENGTH} words:\n"


def main():
    my_config = config.load_config()
    my_reddit = reddit.login()
    thread = reddit.get_thread(reddit=my_reddit,
                               subreddit=my_config['Reddit']['subreddit'])

    if thread is None:
        print('No thread found!')
        return

    Path(f"./Assets/temp").mkdir(parents=True, exist_ok=True)
    thread_id_path = f"./Assets/temp/{thread.id}"

    # download screenshot of reddit post and its comments
    get_thread_title(reddit_thread=thread)

    # create a mp3 directory for the tts files
    Path(f"{thread_id_path}/mp3").mkdir(parents=True, exist_ok=True)
    Path(f"{thread_id_path}/mp3_clean").mkdir(parents=True, exist_ok=True)
    print("Getting mp3 files..")

    # download tts files
    thread_title = markdown_to_text(thread.title)
    title_audio_path = f'{thread_id_path}/mp3/title.mp3'
    title_audio_clean_path = f'{thread_id_path}/mp3_clean/title.mp3'
    create_tts(text=thread_title, path=title_audio_path)

    # make sure the tts of the title and response don't exceed the total duration
    total_video_duration = my_config['VideoSetup']['total_video_duration']
    pause = my_config['VideoSetup']['pause']
    current_video_duration = 0

    tts_title_path = f'{thread_id_path}/mp3/title.mp3'
    title_duration = get_length(path=tts_title_path)
    current_video_duration += title_duration + pause

    # get OpenAI response
    ai_response = chat_gpt.ask_prompt(ASK_REDDIT_PROMPT + thread_title)
    response_audio_path = f'{thread_id_path}/mp3/ai_response.mp3'
    response_audio_clean_path = f'{thread_id_path}/mp3_clean/ai_response.mp3'
    create_tts(text=ai_response, path=response_audio_path)

    response_audio_duration = get_length(response_audio_path)
    current_video_duration += response_audio_duration

     # convert the pause(in seconds) into milliseconds
    mp3_pause = pause * 1000
    add_pause(title_audio_path, title_audio_clean_path, mp3_pause)
    add_pause(response_audio_path,response_audio_clean_path, mp3_pause)


    title_image_path = f'{thread_id_path}/png/title.png'
    # create final video
    make_subtitled_video(title_audio_path=title_audio_clean_path,
                     answer_audio_path=response_audio_clean_path,
                     title_image_path=title_image_path,
                     length=math.ceil(total_video_duration),
                     reddit_id=thread.id
                     )

    if my_config['App']['upload_to_youtube']:
        upload_file = f'./Results/{thread.id}.mp4'
        directory_path = my_config['Directory']['path']
        cmd = ['python', f'{directory_path}/Youtube/upload.py', '--file', upload_file, '--title',
               f'{thread_title}', '--description', f'{thread_title}']
        subprocess.run(cmd)


if __name__ == '__main__':
    my_config = config.load_config()
    while True:
        print('Starting ..........\n')
        for i in range(10):
            main()
        print('\n-------------------------------------------\n')
        time.sleep(my_config['App']['run_every'])


