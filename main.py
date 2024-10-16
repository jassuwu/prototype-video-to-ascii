#!/usr/bin/env python

import os
import sys
import time
import re
import subprocess
from multiprocessing import Pool, cpu_count

from yt_dlp import YoutubeDL
import cv2 as cv
import numpy as np

CHARS = " .;coPO?#@" # character map
ANGLE_CHARS = "|/_\\"
SCALE_DOWN = 8  # Scaling factor to resize the image
PROGRESS_BAR_LENGTH = 100  # Length of the progress bar
PLAYBACK_SPEED = 1.0  # Set to 0.5 for 0.5x speed, 2.0 for 2x speed, etc.

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

def rgb_to_ansi(r, g, b):
    """Converts RGB values to an ANSI escape code for terminal output."""
    return f"\033[38;2;{r};{g};{b}m"

def convert_to_ascii(img_path):
    # Load the image in both grayscale and RGB
    img_gray = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
    img_color = cv.imread(img_path)

    if img_gray is not None and img_color is not None:
        new_size = (img_gray.shape[1] // SCALE_DOWN, img_gray.shape[0] // SCALE_DOWN)
        
        # Resize both grayscale and color images to the same size
        img_gray = cv.resize(img_gray, new_size)
        img_color = cv.resize(img_color, new_size)
        
        grad_x = cv.Sobel(img_gray, cv.CV_64F, 1, 0, ksize=3)
        grad_y = cv.Sobel(img_gray, cv.CV_64F, 0, 1, ksize=3)
        angle = np.arctan2(grad_y, grad_x) * (180 / np.pi)
        angle = np.where(angle < 0, angle + 180, angle)

        edges_down = cv.Canny(img_gray, 100, 200)
        img_normalized = img_gray / 255.0
        img_scaled = img_normalized * (len(CHARS) - 1)
        img_indices = img_scaled.astype(int)

        grad_x_down = cv.resize(grad_x, new_size)
        grad_y_down = cv.resize(grad_y, new_size)
        angle_down = np.arctan2(grad_y_down, grad_x_down) * (180 / np.pi)
        angle_down = np.where(angle_down < 0, angle_down + 180, angle_down)

        # Create ASCII art with colored output
        output = []
        for i in range(img_indices.shape[0]):
            row = []
            for j in range(img_indices.shape[1]):
                char = CHARS[img_indices[i, j]]
                color = img_color[i, j]
                r, g, b = color[2], color[1], color[0]  # OpenCV uses BGR, so reverse to RGB
                ansi_color = rgb_to_ansi(r, g, b)

                if edges_down[i, j] > 0:
                    ang = angle_down[i, j]
                    if 0 <= ang < 22.5 or 157.5 <= ang < 180:
                        char = ANGLE_CHARS[0]  # _
                    elif 22.5 <= ang < 67.5:
                        char = ANGLE_CHARS[1]  # /
                    elif 67.5 <= ang < 112.5:
                        char = ANGLE_CHARS[2]  # |
                    elif 112.5 <= ang < 157.5:
                        char = ANGLE_CHARS[3]  # \

                row.append(f"{ansi_color}{char}\033[0m")  # Reset color after each character

            output.append("".join(row))

        ascii_art = "\n".join(output)
        return ascii_art

    return ""

def play_audio(video_path, speed=1.0):
    return subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-vf', f'setpts={1/speed}*PTS', video_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def extract_number(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else float('inf')

def print_progress_bar(completed, total, bar_length=PROGRESS_BAR_LENGTH):
    percent = (completed / total) * 100
    filled_length = int(bar_length * completed // total)
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {completed}/{total} {percent:.2f}% Complete', end='')


# Modify the display_frame function
def display_frame(ascii_art, frame_duration):
    start_time = time.time()
    os.system("clear")
    print(ascii_art)
    elapsed_time = time.time() - start_time

    # Adjust the sleep time based on the playback speed
    adjusted_frame_duration = frame_duration / PLAYBACK_SPEED
    sleep_time = adjusted_frame_duration - elapsed_time
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
    play_audio(video_path, PLAYBACK_SPEED)

    for ascii_art in ascii_art_frames:
        display_frame(ascii_art, 1 / int(fps))

if __name__ == "__main__":
    yt_url = sys.argv[1]
    main(yt_url)