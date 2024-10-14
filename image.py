#!/usr/bin/env python

import os
import sys
import cv2 as cv
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Define constants
SCALE_DOWN = 4  # Adjust this for image size
CHARS = " .:-=+*%@#"  # Character map
ANGLE_CHARS = "|/_\\"  # Characters for edge directions

def convert_to_ascii(img_path):
    img_color = cv.imread(img_path)
    img_gray = cv.cvtColor(img_color, cv.COLOR_BGR2GRAY)

    if img_gray is not None:
        new_size = (img_gray.shape[1] // SCALE_DOWN, img_gray.shape[0] // SCALE_DOWN)
        img_gray = cv.resize(img_gray, new_size)
        img_color = cv.resize(img_color, new_size)  # Resize color image

        # Compute gradients for edge direction
        grad_x = cv.Sobel(img_gray, cv.CV_64F, 1, 0, ksize=3)
        grad_y = cv.Sobel(img_gray, cv.CV_64F, 0, 1, ksize=3)
        angle = np.arctan2(grad_y, grad_x) * (180 / np.pi)
        angle = np.where(angle < 0, angle + 180, angle)

        # Edge detection
        edges_down = cv.Canny(img_gray, 100, 200)

        # Normalize and scale the image
        img_normalized = img_gray / 255.0
        img_scaled = img_normalized * (len(CHARS) - 1)
        img_indices = img_scaled.astype(int)

        ascii_output = []
        color_output = []
        for i in range(img_indices.shape[0]):
            row = []
            color_row = []
            for j in range(img_indices.shape[1]):
                char = CHARS[img_indices[i, j]]  # Default character from brightness
                row.append(char)

                # Get the color of the corresponding pixel
                color = img_color[i, j]
                hex_color = "#{:02x}{:02x}{:02x}".format(color[2], color[1], color[0])  # Convert BGR to RGB hex
                color_row.append(hex_color)

                # Edge direction mapping
                if edges_down[i, j] > 0:  # If the pixel is an edge
                    ang = angle[i, j]
                    if 0 <= ang < 22.5 or 157.5 <= ang < 180:
                        char = ANGLE_CHARS[0]  # Vertical
                    elif 22.5 <= ang < 67.5:
                        char = ANGLE_CHARS[1]  # /
                    elif 67.5 <= ang < 112.5:
                        char = ANGLE_CHARS[2]  # Horizontal
                    elif 112.5 <= ang < 157.5:
                        char = ANGLE_CHARS[3]  # \

                row[-1] = char  # Update row with the character (including edges)

            ascii_output.append(row)
            color_output.append(color_row)

        return ascii_output, color_output

    return [], []


def save_ascii_as_image(ascii_art, colors, output_path):
    height = len(ascii_art)
    width = len(ascii_art[0])
    
    # Create a new blank image
    output_img = Image.new("RGB", (width * 10, height * 20), "black")
    draw = ImageDraw.Draw(output_img)
    
    # Load a font (you can specify your own font path)
    try:
        font = ImageFont.truetype("font.ttf", 20)  # Ensure this font is available
    except IOError:
        print("Font not found, using default font.")
        font = ImageFont.load_default()
    
    # Draw ASCII characters on the image with color
    for y in range(height):
        for x in range(width):
            char = ascii_art[y][x]
            hex_color = colors[y][x]
            draw.text((x * 10, y * 20), char, fill=hex_color, font=font)

    # Save the ASCII art image
    output_img.save(output_path)

def main(image_path, output_path):
    ascii_art, colors = convert_to_ascii(image_path)
    if ascii_art:
        save_ascii_as_image(ascii_art, colors, output_path)
        print(f"ASCII art saved as {output_path}")
    else:
        print("Could not convert image to ASCII.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ascii_image.py <path_to_image> <output_image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2]
    main(image_path, output_path)