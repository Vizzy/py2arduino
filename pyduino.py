#!/usr/bin/env python3.3

import os, subprocess
from argparse import ArgumentParser

from compiler import translate
import config

def write_translation(translated, filename, extension='ino'):
    
    try:
        os.mkdir(sketchname)
    except OSError:
        pass

    filename = os.path.split(filename)[1]

    sketchpath = os.path.join(sketchname, (filename.split('.')[0] + '.' + extension))
    with open(sketchpath, 'w') as sketch:
        sketch.write(translated)

def run(sketchname, upload=False):
    if upload:
        run_flag = '--upload'
    else:
        run_flag = '--verify'

    sketchpath = os.path.join(sketchname, sketchname + '.ino')
    sketchpath = os.path.abspath(sketchpath)
    subprocess.call([config.arduino_path,
                    args.board,
                    args.port,
                    run_flag,
                    sketchpath])

def main():
    global sketchname

    sketchname = os.path.split(args.file)[1].split('.py')[0]

    sketchfile = open(args.file)
    translated = translate(sketchfile.read())

    write_translation(translated['code'], sketchname)

    if args.compile:
        run(sketchname)
    elif args.upload:
        run(sketchname, upload=True)

if __name__ == '__main__':
    argp = ArgumentParser()
    argp.add_argument('file', type=str, help='file to parse')
    argp.add_argument('-v', '--verbose', action='store_true', default=False,
     help='verbose mode')
    argp.add_argument('-w', action='store_true', default=False, 
        help='suppress warnings')

    # options for compilation
    argp.add_argument('-c', '--compile', action='store_true', 
        default=False, help='compile the script')
    argp.add_argument('-b', '--board', type=str, default='uno', 
        help='board type to compile for')
    argp.add_argument('-p', '--port', default='/dev/ttyusb', type=str,
        help='arduino serial port')
    argp.add_argument('-u', '--upload', action='store_true', default=False, 
        help='upload the script to the board (works only if -c or --compile is specified')
    args = argp.parse_args()

    if args.w:
        simplefilter('ignore')

    main()
