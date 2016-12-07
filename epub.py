#!/usr/bin/env python
'''
python/curses epub reader. Requires BeautifulSoup

Keyboard commands:
    Esc/q          - quit
    Tab/Left/Right - toggle between TOC and chapter views
    TOC view:
        Up         - up a line
        Down       - down a line
        PgUp       - up a page
        PgDown     - down a page
    Chapter view:
        Up         - up a page
        Down       - down a page
        PgUp       - up a line
        PgDown     - down a line
        i          - open images on page in web browser
'''

import curses.wrapper
import curses.ascii
import formatter
import htmllib
import locale
import os
import StringIO
import re
import tempfile
import zipfile

from bs4 import BeautifulSoup

try:
    from fabulous import image
    import Pillow
except ImportError:
    images = False
else:
    images = True

locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

basedir = ''

ESCAPE_KEYS = [ord('q'), curses.ascii.ESC]
TOC_DOWN_LINE_KEYS = [curses.KEY_DOWN]
TOC_UP_LINE_KEYS = [curses.KEY_UP]
TOC_DOWN_PAGE_KEYS = [curses.KEY_NPAGE]
TOC_UP_PAGE_KEYS = [curses.KEY_PPAGE]
CHAPTER_DOWN_PAGE_KEYS = [curses.KEY_DOWN]
CHAPTER_UP_PAGE_KEYS = [curses.KEY_UP]
CHAPTER_DOWN_LINE_KEYS = [curses.KEY_NPAGE]
CHAPTER_UP_LINE_KEYS = [curses.KEY_PPAGE]
CHAPTERTOCSWITCH_KEYS = [curses.ascii.HT, curses.KEY_RIGHT, curses.KEY_LEFT]

def run(screen, program, *args):
    curses.nocbreak()
    screen.keypad(0)
    curses.echo()
    pid = os.fork()
    if not pid:
        os.execvp(program, (program,) + args)
    os.wait()[0]
    curses.noecho()
    screen.keypad(1)
    curses.cbreak()


def open_image(screen, name, s):
    ''' show images with PIL and fabulous '''
    if not images:
        screen.addstr(0, 0, "missing PIL or fabulous", curses.A_REVERSE)
        return

    ext = os.path.splitext(name)[1]

    screen.erase()
    screen.refresh()
    curses.setsyx(0, 0)
    image_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    image_file.write(s)
    image_file.close()
    try:
        print image.Image(image_file.name)
    except:
        print image_file.name
    finally:
        os.unlink(image_file.name)


def textify(html_snippet, img_size=(80, 45), maxcol=72):
    ''' text dump of html '''
    class Formatter(formatter.AbstractFormatter):
        pass

    class Parser(htmllib.HTMLParser):

        def anchor_end(self):
            self.anchor = None

        def handle_image(self, source, alt, ismap, alight, width, height):
            global basedir
            self.handle_data(
                '[img="{0}{1}" "{2}"]'.format(basedir, source, alt)
            )

    class Writer(formatter.DumbWriter):

        def __init__(self, fl, maxcol=72):
            formatter.DumbWriter.__init__(self, fl)
            self.maxcol = maxcol

        def send_label_data(self, data):
            self.send_flowing_data(data)
            self.send_flowing_data(' ')

    o = StringIO.StringIO()
    p = Parser(Formatter(Writer(o, maxcol)))
    p.feed(html_snippet)
    p.close()

    return o.getvalue()


def table_of_contents(fl):
    global basedir

    # find opf file
    soup = BeautifulSoup(fl.read('META-INF/container.xml'))
    opf = dict(soup.find('rootfile').attrs)['full-path']

    basedir = os.path.dirname(opf)
    if basedir:
        basedir = '{0}/'.format(basedir)

    soup = BeautifulSoup(fl.read(opf))

    # title
    yield (soup.find('dc:title').text, None)

    # all files, not in order
    x, ncx = {}, None
    for item in soup.find('manifest').findAll('item'):
        d = dict(item.attrs)
        x[d['id']] = '{0}{1}'.format(basedir, d['href'])
        if d['media-type'] == 'application/x-dtbncx+xml':
            ncx = '{0}{1}'.format(basedir, d['href'])

    # reading order, not all files
    y = []
    for item in soup.find('spine').findAll('itemref'):
        y.append(x[dict(item.attrs)['idref']])

    z = {}
    if ncx:
        # get titles from the toc
        soup = BeautifulSoup(fl.read(ncx))

        for navpoint in soup('navpoint'):
            k = navpoint.content.get('src', None)
            # strip off any anchor text
            k = k.split('#')[0]
            if k:
                z[k] = navpoint.navlabel.text

    # output
    for section in y:
        if section in z:
            yield (z[section].encode('utf-8'), section.encode('utf-8'))
        else:
            yield (u'', section.encode('utf-8').strip())


def list_chaps(screen, chaps, start, length):
    for i, (title, src) in enumerate(chaps[start:start + length]):
        try:
            if start == 0:
                screen.addstr(i, 0, '      {0}'.format(title), curses.A_BOLD)
            else:
                screen.addstr(i, 0, '{0:-5} {1}'.format(start, title))
        except:
            pass
        start += 1
    screen.refresh()
    return i


def check_epub(fl):
    if os.path.isfile(fl) and os.path.splitext(fl)[1].lower() == '.epub':
        return True


def dump_epub(fl, maxcol=float("+inf")):
    if not check_epub(fl):
        return
    fl = zipfile.ZipFile(fl, 'r')
    chaps = [i for i in table_of_contents(fl)]
    for title, src in chaps:
        print title
        print '-' * len(title)
        if src:
            soup = BeautifulSoup(fl.read(src))
            print textify(
                unicode(soup.find('body')).encode('utf-8'),
                maxcol=maxcol,
            )
        print '\n'


def curses_epub(screen, fl):
    if not check_epub(fl):
        return

    #curses.mousemask(curses.BUTTON1_CLICKED)

    fl = zipfile.ZipFile(fl, 'r')
    chaps = [i for i in table_of_contents(fl)]
    chaps_pos = [0 for i in chaps]
    start = 0
    cursor_row = 0

    # toc
    while True:
        curses.curs_set(1)
        maxy, maxx = screen.getmaxyx()

        if cursor_row >= maxy:
            cursor_row = maxy - 1

        len_chaps = list_chaps(screen, chaps, start, maxy)
        screen.move(cursor_row, 0)
        ch = screen.getch()

        if ch in ESCAPE_KEYS:
            return

        # up/down line
        if ch in TOC_DOWN_LINE_KEYS:
            if start < len(chaps) - maxy:
                start += 1
                screen.clear()
            elif cursor_row < maxy - 1 and cursor_row < len_chaps:
                cursor_row += 1
        elif ch in TOC_UP_LINE_KEYS:
            if start > 0:
                start -= 1
                screen.clear()
            elif cursor_row > 0:
                cursor_row -= 1

        # up/down page
        elif ch in TOC_DOWN_PAGE_KEYS:
            if start + maxy - 1 < len(chaps):
                start += maxy - 1
                if len_chaps < maxy:
                    start = len(chaps) - maxy
                screen.clear()
        elif ch in TOC_UP_PAGE_KEYS:
            if start > 0:
                start -= maxy - 1
                if start < 0:
                    start = 0
                screen.clear()

        # to chapter
        elif ch in CHAPTERTOCSWITCH_KEYS:
            if chaps[start + cursor_row][1]:
                html = fl.read(chaps[start + cursor_row][1])
                soup = BeautifulSoup(html)
                chap = textify(
                    unicode(soup.find('body')).encode('utf-8'),
                    img_size=screen.getmaxyx(),
                    maxcol=screen.getmaxyx()[1]
                ).split('\n')
            else:
                chap = ''
            screen.clear()
            curses.curs_set(0)

            # chapter
            while True:
                maxy, maxx = screen.getmaxyx()
                images = []
                for i, line in enumerate(chap[
                    chaps_pos[start + cursor_row]:
                    chaps_pos[start + cursor_row] + maxy
                ]):
                    try:
                        screen.addstr(i, 0, line)
                        mch = re.search('\[img="([^"]+)" "([^"]*)"\]', line)
                        if mch:
                            images.append(mch.group(1))
                    except:
                        pass
                screen.refresh()
                ch = screen.getch()

                # quit
                if ch in ESCAPE_KEYS:
                    return

                # to TOC
                if ch in CHAPTERTOCSWITCH_KEYS:
                    screen.clear()
                    break

                # up/down page
                elif ch in CHAPTER_DOWN_PAGE_KEYS:
                    if chaps_pos[start + cursor_row] + maxy - 1 < len(chap):
                        chaps_pos[start + cursor_row] += maxy - 1
                        screen.clear()
                elif ch in CHAPTER_UP_PAGE_KEYS:
                    if chaps_pos[start + cursor_row] > 0:
                        chaps_pos[start + cursor_row] -= maxy - 1
                        if chaps_pos[start + cursor_row] < 0:
                            chaps_pos[start + cursor_row] = 0
                        screen.clear()

                # up/down line
                elif ch in CHAPTER_DOWN_LINE_KEYS:
                    if chaps_pos[start + cursor_row] + maxy - 1 < len(chap):
                        chaps_pos[start + cursor_row] += 1
                        screen.clear()
                elif ch in CHAPTER_UP_LINE_KEYS:
                    if chaps_pos[start + cursor_row] > 0:
                        chaps_pos[start + cursor_row] -= 1
                        screen.clear()

                #elif ch in [curses.KEY_MOUSE]:
                #    id, x, y, z, bstate = curses.getmouse()
                #    line = screen.instr(y, 0)
                #    mch = re.search('\[img="([^"]+)" "([^"]*)"\]', line)
                #    if mch:
                #            img_fl = mch.group(1)

                else:
                    try:
                        if chr(ch) == 'i':
                            for img in images:
                                try:
                                    err = open_image(screen, img, fl.read(img))
                                except KeyError:
                                    err = 'image not found'
                                if err:
                                    screen.addstr(0, 0, err, curses.A_REVERSE)

                        # edit html
                        elif chr(ch) == 'e':

                            tmpfl = tempfile.NamedTemporaryFile(delete=False)
                            tmpfl.write(html)
                            tmpfl.close()
                            run(screen, 'vim', tmpfl.name)
                            with open(tmpfl.name) as changed:
                                new_html = changed.read()
                                os.unlink(tmpfl.name)
                                if new_html != html:
                                    pass
                                    # write to zipfile?

                            # go back to TOC
                            screen.clear()
                            break

                    except (ValueError, IndexError):
                        pass

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument(
        '-d', '--dump',
        action='store_true',
        help='dump EPUB to text'
    )
    parser.add_argument(
        '-c', '--cols',
        action='store',
        type=int,
        default=float("+inf"),
        help='Number of columns to wrap; default is no wrapping.'
    )
    parser.add_argument('EPUB', help='view EPUB')
    args = parser.parse_args()

    if args.EPUB:
        if args.dump:
            dump_epub(args.EPUB, args.cols)
        else:
            try:
                curses.wrapper(curses_epub, args.EPUB)
            except KeyboardInterrupt:
                pass
