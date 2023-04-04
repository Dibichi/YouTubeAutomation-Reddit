import os
import re
import multiprocessing
from os.path import exists
from typing import Tuple, Any, Final

from pathlib import Path
from typing import Tuple, Any
from PIL import Image
import random

from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from moviepy.video.fx.resize import resize
from moviepy.video.fx.crop import crop
from moviepy.video.fx.speedx import speedx
from moviepy.editor import *

import random
import time
import config
import OpenAI.speech_to_text as stt

def prepare_random_background(length, W, H):
    my_config = config.load_config()
    video_folder = Path(my_config['Background']['path_folder'])

    potential_videos = list(video_folder.glob('*'))
    
    counter = 0
    vide_duration = 0
    video = False
    while(counter <= len(potential_videos)):
        video_path = random.choice(potential_videos)
        video = VideoFileClip(str(video_path)).without_audio()
        vide_duration = video.duration

        if (vide_duration >= length):
            break
        

    random_start = random.randint(0, int(vide_duration))
    vid = video.subclip(random_start, random_start+length)
    video.close()

    vid_resized = resize(vid, height=H)
    clip = (
        vid_resized
    )
    # calculate the center of the background clip
    c = clip.w // 2

    # calculate the coordinates where to crop
    half_w = W // 2
    x1 = c - half_w
    x2 = c + half_w

    return crop(clip, x1=x1, y1=0, x2=x2, y2=H)

def prepare_background(reddit_id,length,W, H):
    my_config = config.load_config()

    video = VideoFileClip(my_config['Background']['path']).without_audio()
    vide_duration = video.duration

    random_start = random.randint(0, int(vide_duration))
    vid = video.subclip(random_start, random_start+length)
    video.close()

    vid_resized = resize(vid, height=H)
    clip = (
        vid_resized
    )
    # calculate the center of the background clip
    c = clip.w // 2

    # calculate the coordinates where to crop
    half_w = W // 2
    x1 = c - half_w
    x2 = c + half_w

    return crop(clip, x1=x1, y1=0, x2=x2, y2=H)

def make_final_video(
    title_audio_path,
    comments_audio_path,
    title_image_path,
    comments_image_path,
    length: int,
    reddit_id,

):
    # settings values
    W = 1080
    H = 1920
    opacity = 0.95

    print("Creating the final video 🎥")
    background_clip = prepare_background(reddit_id,length,W,H)



    # Gather all audio clips
    audio_clips = [
        AudioFileClip(i)
        for i in comments_audio_path
    ]

    audio_clips.insert(0, AudioFileClip(title_audio_path))
    audio_concat = concatenate_audioclips(audio_clips)

    audio_composite = CompositeAudioClip([audio_concat])

    print(f"Video Will Be: {length} Seconds Long")

    # add title to video
    image_clips = []
    # Gather all images

    new_opacity = 1 if opacity is None or float(opacity) >= 1 else float(opacity)

    screenshot_width = int((W * 90) // 100)

    title = ImageClip(title_image_path).set_duration(audio_clips[0].duration).set_opacity(new_opacity).set_position("center")
    resized_title = resize(title, width=screenshot_width)
    image_clips.insert(
        0,
        resized_title,
    )

    for idx, i in enumerate(comments_image_path):
        comment = ImageClip(i).set_duration(audio_clips[idx + 1].duration).set_opacity(new_opacity).set_position("center")
        resized_comment = resize(comment, width=screenshot_width)
        image_clips.append(
            resized_comment
        )

    image_concat = concatenate_videoclips(image_clips,)  # note transition kwarg for delay in imgs
    image_concat.audio = audio_composite
    audio_composite.close()
    final = CompositeVideoClip([background_clip, image_concat.set_position("center")])
    image_concat.close()

    subreddit = reddit_id

    final.write_videofile(
        f"./Results/{subreddit}.mp4",
        fps=int(24),
        audio_codec="aac",
        audio_bitrate="192k",
        threads=multiprocessing.cpu_count(),
        #preset="ultrafast", # for testing purposes
    )
    final.close()

    print("See result in the results folder!")


def update_subtitle_times(time_update, subtitles):
    for timestamps in subtitles:
        timestamps[0] = timestamps[0] + time_update


def make_subtitled_video(
    title_audio_path,
    answer_audio_path,
    title_image_path,
    length: int,
    reddit_id,

):
    # settings values
    W = 1080
    H = 1920
    opacity = 0.95

    print("Creating the final video 🎥")
    background_clip = prepare_random_background(length,W,H)

    # Gather all audio clips
    audio_clips = [AudioFileClip(title_audio_path), AudioFileClip(answer_audio_path)]
    audio_concat = concatenate_audioclips(audio_clips)
    audio_composite = CompositeAudioClip([audio_concat])

    print(f"Video Will Be: {length} Seconds Long")

    # add title to video
    image_clips = []
    # Gather all images

    new_opacity = 1 if opacity is None or float(opacity) >= 1 else float(opacity)

    screenshot_width = int((W * 90) // 100)

    title = ImageClip(title_image_path).set_duration(audio_clips[0].duration).set_opacity(new_opacity).set_position("center")
    title_duration = audio_clips[0].duration
    resized_title = resize(title, width=screenshot_width)

    subs = stt.create_srt(answer_audio_path, title_duration)
    
    generator = lambda txt: TextClip(txt, font='P052-Bold', fontsize=H/25, stroke_width=1, color='yellow', stroke_color = 'black', size = (W, H*.25), method='caption')
    subtitles = SubtitlesClip(subs, generator)

    if(audio_composite.duration > length):
        speed_multiplier =  audio_composite.duration / length 
        audio_composite = audio_composite.fx(speedx, speed_multiplier)
        subtitles = subtitles.fx(speedx, speed_multiplier)

    image_clips.insert(
        0,
        resized_title,
    )

    image_concat = concatenate_videoclips(image_clips,)  # note transition kwarg for delay in imgs
    image_concat.audio = audio_composite
    audio_composite.close()
    
    final = CompositeVideoClip([background_clip, image_concat.set_position("center"), subtitles.set_position("center")]).subclip(0, audio_composite.duration)

    image_concat.close()

    subreddit = reddit_id

    final.write_videofile(
        f"./Results/{subreddit}.mp4",
        fps=int(24),
        audio_codec="aac",
        audio_bitrate="192k",
        threads=multiprocessing.cpu_count(),
        #preset="ultrafast", # for testing purposes
    )
    final.close()

    print("See result in the results folder!")
