#!/usr/bin/env python
import cv2 as cv
import os
import time
import re
import subprocess
from multiprocessing import Pool, cpu_count

CHARS = " .;coPO?@#" # character map
FRAMES_DIR = "frames/animu8k" # folder with the frames data generated from ffmpeg
FRAME_EXT = ".jpg" # extension of the frames in the FRAMES_DIR
VIDEO_SRC = "videos/animu8k.webm" # video_file name to play the audio during the rendering
SCALE_DOWN = 16  # Scaling factor to resize the image
FRAME_RATE = 1 / 60  # Frame rate (60 FPS for the video)
PROGRESS_BAR_LENGTH = 100  # Length of the progress bar

def convert_to_ascii(img_path):
    img = cv.imread(img_path, cv.IMREAD_GRAYSCALE)
    if img is not None:
        img_down = cv.resize(img, (img.shape[1] // SCALE_DOWN, img.shape[0] // SCALE_DOWN))
        img_normalized = img_down // 255  # Scale pixel values to [0, 1]
        img_scaled = img_normalized * (len(CHARS) - 1)  # Scale to [0, len(CHARS) - 1]
        img_indices = img_scaled.astype(int)
        return "\n".join("".join(CHARS[idx] for idx in row) for row in img_indices)
    return ""

def play_audio():
    return subprocess.Popen(['ffplay', '-nodisp', '-autoexit', VIDEO_SRC], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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

def main():
    frame_files = [f for f in os.listdir(FRAMES_DIR) if f.endswith(FRAME_EXT)]
    if not frame_files:
        print("No frames found in the directory.")
        return

    # Sort files numerically
    frame_files.sort(key=extract_number)
    frame_paths = [os.path.join(FRAMES_DIR, f) for f in frame_files]

    # Show progress meter for conversion
    print("Processing frames to ASCII")
    total_frames = len(frame_paths)
    ascii_art_frames = []

    with Pool(cpu_count()) as pool:
        for idx, ascii_art in enumerate(pool.imap(convert_to_ascii, frame_paths), start=1):
            ascii_art_frames.append(ascii_art)
            print_progress_bar(idx, total_frames)
#     for idx, frame in enumerate(frame_paths):
#         ascii_art_frames.append(convert_to_ascii(frame))
#         print_progress_bar(idx, total_frames)

    print()
    play_audio() # actually the audio

    for ascii_art in ascii_art_frames:
        display_frame(ascii_art, FRAME_RATE)

if __name__ == "__main__":
    main()
