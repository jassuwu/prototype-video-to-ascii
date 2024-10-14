#!/usr/bin/env python

import os
import sys
import time
import re
import subprocess
from multiprocessing import Pool, cpu_count
import math
import threading
import cv2 as cv
import numpy as np
from yt_dlp import YoutubeDL
import curses

# Define constants
SCALE_DOWN = 2
CHARS = " .;coPO?#@" # character map
ANGLE_CHARS = "|/_\\"
PROGRESS_BAR_LENGTH = 100

# Functions for downloading video and extracting frames
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

    cap = cv.VideoCapture(video_path)
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
    img_gray = cv.imread(img_path, cv.IMREAD_GRAYSCALE)

    if img_gray is not None:
        new_size = (img_gray.shape[1] // SCALE_DOWN, img_gray.shape[0] // SCALE_DOWN)
        img_gray = cv.resize(img_gray, new_size)

        grad_x = cv.Sobel(img_gray, cv.CV_64F, 1, 0, ksize=3)
        grad_y = cv.Sobel(img_gray, cv.CV_64F, 0, 1, ksize=3)
        angle = np.arctan2(grad_y, grad_x) * (180 / np.pi)
        angle = np.where(angle < 0, angle + 180, angle)

        edges_down = cv.Canny(img_gray, 100, 200)
        img_normalized = img_gray / 255.0
        img_scaled = img_normalized * (len(CHARS) - 1)
        img_indices = img_scaled.astype(int)

        output = []
        for i in range(img_indices.shape[0]):
            row = []
            for j in range(img_indices.shape[1]):
                char = CHARS[img_indices[i, j]]
                if edges_down[i, j] > 0:
                    ang = angle[i, j]
                    if 0 <= ang < 22.5 or 157.5 <= ang < 180:
                        char = ANGLE_CHARS[0]
                    elif 22.5 <= ang < 67.5:
                        char = ANGLE_CHARS[1]
                    elif 67.5 <= ang < 112.5:
                        char = ANGLE_CHARS[2]
                    elif 112.5 <= ang < 157.5:
                        char = ANGLE_CHARS[3]

                row.append(char)

            output.append(row)

        return output

    return ""

def play_audio(video_path):
    return subprocess.Popen(['ffplay', '-nodisp', '-autoexit', video_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def play_audio_async(video_path):
    audio_thread = threading.Thread(target=play_audio, args=(video_path,))
    audio_thread.start()

def extract_number(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else float('inf')

def print_progress_bar(completed, total, bar_length=PROGRESS_BAR_LENGTH):
    percent = (completed / total) * 100
    filled_length = int(bar_length * completed // total)
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r[{bar}] {completed}/{total} {percent:.2f}% Complete', end='')

# Main display function
def display_ascii_frames_with_curses(ascii_art_frames, fps):
    """Display ASCII frames using curses for optimized terminal output."""
    def render_frames(stdscr):
        frame_duration = 1 / fps
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.curs_set(0)
        height, width = stdscr.getmaxyx()

        for ascii_art in ascii_art_frames:
            start_time = time.time()
            stdscr.clear()

            for i, row in enumerate(ascii_art):
                if i >= height:
                    break

                stdscr.addstr(i, 0, ''.join(row[:width]))

            stdscr.refresh()
            elapsed_time = time.time() - start_time
            sleep_time = frame_duration - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    curses.wrapper(render_frames)

# Main execution
def main(yt_url):
    video_path = download_yt_video(yt_url)
    frames_dir, fps = extract_frames(get_video_id(yt_url))

    frame_files = os.listdir(frames_dir)
    if not frame_files:
        print("No frames found in the directory.")
        return

    frame_files.sort(key=extract_number)
    frame_paths = [os.path.join(frames_dir, f) for f in frame_files]

    print("Processing frames to ASCII")
    ascii_art_frames = []

    with Pool(cpu_count()) as pool:
        for ascii_art in pool.imap(convert_to_ascii, frame_paths):
            ascii_art_frames.append(ascii_art)
    
    play_audio_async(video_path)
    display_ascii_frames_with_curses(ascii_art_frames, fps)

if __name__ == "__main__":
    yt_url = sys.argv[1]
    main(yt_url)
