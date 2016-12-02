#!/usr/bin/env python2

"""Convert 8-bit bmp to wav to display in a spectrogram."""

from __future__ import print_function
import argparse
import math
import numpy as np
import os
import struct
import time
import wave
from PIL import Image

def timeit(func):
    def timer(*args, **kwargs):
        before = time.time()
        ret = func(*args, **kwargs)
        print("{}: {}".format(func.__name__, time.time() - before))
        return ret
    return timer


def get_rows(image):
    """Get a list of rows of pixeldata.

    :param image: PIL.Image
    :returns: A list of rows where each row is a list of pixel values
    :rtype: list(np.array, np.array, np.array, ...)
    """

    pixels = np.array(image.getdata())
    w, h = image.size
    return np.array([np.array(pixels[i:i+w]) for i in xrange(0, w*h, w)])


def normalize(frames):
    max_frame = max(frames)
    scalar = 0x7ff / max_frame
    return [int(scalar * val) for val in frames]


@timeit
def convert_image(rows, framerate=11025, frequency=3000, bandwidth=2000, hold=40):
    """Convert an image into audio sampling frames.

    :param rows: A list of pixeldata for each row. Each row is a list of pixel values.
    :param framerate: Output sampling frequency
    :param frequency: Output frequency around which to center the image
    :param bandwidth: Desired bandwidth for the image. This should be proportional to
        the hold param to balance width/heigh in the waterfall display.
    :param hold: Number of milliseconds to hold a specific signal for a row
    """

    # Center the image around the specified frequency
    base_freq = frequency - int(bandwidth / 2)
    frames_per_row = framerate * hold / 1000

    # Generate an array of frequencies we'll be manipulating
    height, width = rows.shape
    total_frames = height * frames_per_row

    # Get frequencies to manipulate and do some pre-processing for optimization
    freqs = np.linspace(base_freq, base_freq+bandwidth, width)
    freqs *= 2 * np.pi / framerate

    # Generate a matrix of signals
    frame_nos = np.arange(total_frames)
    signals = np.array([np.cos(freqs[i] * frame_nos) for i in xrange(width)])
    signals = signals.T

    # Generate a matrix of amplitudes
    amps = np.array([rows[i/frames_per_row] for i in xrange(total_frames)])

    # Apply the amplitudes element-wise to the signals and generate the frames
    return [np.sum(group) for group in np.multiply(amps, signals)]
    


def write_wav(outfile, frames, framerate=11025):
    # Normalize frames to 16-bit signed ints
    norm_frames = normalize(frames)
    raw_frames = "".join(struct.pack("<h", val) for val in norm_frames)

    # Write the wav file
    wav = wave.open(outfile, "wb")
    wav.setparams((1, 2, framerate, 0, "NONE", "not compressed"))
    wav.writeframes(raw_frames)
    wav.close()


def signal(outfile, frequency=5000, amplitude=5000, framerate=44100, duration=5):
    wav = wave.open(outfile, "wb")
    wav.setparams((1, 2, framerate, 0, "NONE", "not compressed"))
    
    for i in xrange(0, framerate * duration):
        value = amplitude * math.sin(2 * math.pi * frequency * i / framerate)
        wav.writeframes(struct.pack("<h", value))
    wav.close()

def main(infile, outfile):
    im = Image.open(infile)
    rows = get_rows(im)
    frames = convert_image(rows, framerate=44100, frequency=11000, bandwidth=18000)
    write_wav(outfile, frames, framerate=44100)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=str,
                        help="8-bit bmp image to process")
    parser.add_argument("-o", "--output", type=str,
                        help="Output file to write the wav to")
    args = parser.parse_args()

    if args.output is None:
        fname, _ = os.path.splitext(args.input)
        args.output = "{}.wav".format(fname)

    main(args.input, args.output)