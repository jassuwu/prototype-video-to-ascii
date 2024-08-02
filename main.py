#!/usr/bin/env python

import os
import sys
import time
import re
import subprocess
from multiprocessing import Pool, cpu_count

from yt_dlp import YoutubeDL
import cv2 as cv

CHARS = " .;coPO?#@" # character map
SCALE_DOWN = 8  # Scaling factor to resize the image
PROGRESS_BAR_LENGTH = 100  # Length of the progress bar

def get_video_id(yt_url):
    video_id_match = re.search(r'(?:v=|\/|embed\/)([a-zA-Z0-9_-]{11})', yt_url)
    if video_id_match:
        return video_id_match.group(1)
    else:
        raise ValueError("Invalid YouTube URL")

def download_yt_video(yt_url):
    if not os.path.isdir("videos"):
        os.mkdir("videos")

    video_id = get_video_id(yt_url)
    output_path = f"videos/{video_id}.mp4"

    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
    }

    with YoutubeDL(ydl_opts) as ydl_instance:
        ydl_instance.download([yt_url])

    os.system("clear")
    return output_path

def extract_frames(video_id):
    video_path = f"videos/{video_id}.mp4"
    frames_dir = f"frames/{video_id}"

    # Open video file
    cap = cv.VideoCapture(video_path)

    # Get total number of frames in the video
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT)) - 1
    fps = cap.get(cv.CAP_PROP_FPS)

    if not os.path.isdir(frames_dir):
        os.makedirs(frames_dir)
    else:
        print(f"frames dir for {video_path} already exists.")
        return frames_dir, fps

    count = 0
    success = True

    print("Processing video to frames")
    while success:
        success, frame = cap.read()
        if success:
            frame_filename = f"{frames_dir}/{count}.jpg"
            cv.imwrite(frame_filename, frame)
        count += 1
        print_progress_bar(count, total_frames)

    cap.release()
    print()  # Move to the next line after progress bar
    os.system("clear")

    return frames_dir, fps

def convert_to_ascii(img_path):
    img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
    if img is not None:
        img_down = cv.resize(img, (img.shape[1] // SCALE_DOWN, img.shape[0] // SCALE_DOWN))
        img_normalized = img_down / 255.0  # Scale pixel values to [0, 1]
        img_scaled = img_normalized * (len(CHARS) - 1)  # Scale to [0, len(CHARS) - 1]
        img_indices = img_scaled.astype(int)
        return "\n".join("".join(CHARS[idx] for idx in row) for row in img_indices)
    return ""

def play_audio(video_path):
    return subprocess.Popen(['ffplay', '-nodisp', '-autoexit', video_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def extract_number(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else float('inf')

def print_progress_bar(completed, total, bar_length=PROGRESS_BAR_LENGTH):
    percent = (completed / total) * 100
    filled_length = int(bar_length * completed // total)
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {completed}/{total} {percent:.2f}% Complete', end='')

def display_frame(ascii_art, frame_duration):
    start_time = time.time()
    os.system("clear")
    print(ascii_art)
    elapsed_time = time.time() - start_time
    sleep_time = frame_duration - elapsed_time
    if sleep_time > 0:
        time.sleep(sleep_time)

def main(yt_url):
    video_path = download_yt_video(yt_url)

    frames_dir, fps = extract_frames(get_video_id(yt_url))

    frame_files = os.listdir(frames_dir)
    if not frame_files:
        print("No frames found in the directory.")
        return

    # Sort files numerically
    frame_files.sort(key=extract_number)
    frame_paths = [os.path.join(frames_dir, f) for f in frame_files]

    # Show progress meter for conversion
    print("Processing frames to ASCII")
    total_frames = len(frame_paths)
    ascii_art_frames = []

    with Pool(cpu_count()) as pool:
        for idx, ascii_art in enumerate(pool.imap(convert_to_ascii, frame_paths), start=1):
            ascii_art_frames.append(ascii_art)
            print_progress_bar(idx, total_frames)

    print()
    play_audio(video_path)

    for ascii_art in ascii_art_frames:
        display_frame(ascii_art, 1 / int(fps))

if __name__ == "__main__":
    yt_url = sys.argv[1]
    main(yt_url)
