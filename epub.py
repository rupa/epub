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

import curses.wrapper, curses.ascii
import formatter, htmllib, locale, os, StringIO, re, readline, zipfile
import base64, webbrowser

from BeautifulSoup import BeautifulSoup

locale.setlocale(locale.LC_ALL, 'en_US.utf-8')

def open_image(name, s):
    ''' open an image in webbrowser with a data url '''
    ext = os.path.splitext(name)[1]
    try:
        mime = {
            '.gif': 'image/gif',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }[ext]
    except KeyError as e:
        return
    try:
        webbrowser.open_new_tab('data:{0};base64,{1}'.format(
            mime,
            base64.b64encode(s)
        ))
    except IOError as e:
        pass

def textify(fl, html_snippet, img_size=(80, 45)):
    ''' text dump of html '''
    class Parser(htmllib.HTMLParser):
        def anchor_end(self):
            self.anchor = None
        def handle_image(self, source, alt, ismap, alight, width, height):
            self.handle_data('[img="{0}" "{1}"]'.format(source, alt))

    class Formatter(formatter.AbstractFormatter):
        pass

    class Writer(formatter.DumbWriter):
        def send_label_data(self, data):
            self.send_flowing_data(data)
            self.send_flowing_data(' ')

    o = StringIO.StringIO()
    p = Parser(Formatter(Writer(o)))
    p.feed(html_snippet)
    p.close()

    return o.getvalue()

def table_of_contents(fl):
    soup =  BeautifulSoup(fl.read('content.opf'))

    # title
    yield (soup.find('dc:title').text, None)

    # all files, not in order
    x = {}
    for item in soup.find('manifest').findAll('item'):
        d = dict(item.attrs)
        x[d['id']] = d['href']

    # reading order, not all files
    y = []
    for item in soup.find('spine').findAll('itemref'):
        y.append(x[dict(item.attrs)['idref']])

    soup =  BeautifulSoup(fl.read('toc.ncx'))

    # get titles from the toc
    z = {}
    for navpoint in soup('navpoint'):
        k = navpoint.content.get('src', None)
        if k:
            z[k] = navpoint.navlabel.text

    # output
    for section in y:
        if section in z:
            yield (z[section].encode('utf-8'), section.encode('utf-8'))
        else:
            yield (u'', section.encode('utf-8').strip())

def list_chaps(screen, chaps, start, length):
    for i, (title, src) in enumerate(chaps[start:start+length]):
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

def dump_epub(fl):
    if not check_epub(fl):
        return
    fl = zipfile.ZipFile(fl, 'r')
    chaps = [i for i in table_of_contents(fl)]
    for title, src in chaps:
        print title
        print '-' * len(title)
        if src:
            soup = BeautifulSoup(fl.read(src))
            print textify(fl, unicode(soup.find('body')).encode('utf-8'))
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

        # quit
        if ch == curses.ascii.ESC:
            return
        try:
           if chr(ch) == 'q':
               return
        except:
            pass

        # up/down line
        if ch in [curses.KEY_DOWN]:
            if start < len(chaps) - maxy:
                start += 1
                screen.clear()
            elif cursor_row < maxy - 1 and cursor_row < len_chaps:
                cursor_row += 1
        elif ch in [curses.KEY_UP]:
            if start > 0:
                start -= 1
                screen.clear()
            elif cursor_row > 0:
                cursor_row -= 1

        # up/down page
        elif ch in [curses.KEY_NPAGE]:
            if start + maxy - 1 < len(chaps):
                start += maxy - 1
                if len_chaps < maxy:
                    start = len(chaps) - maxy
                screen.clear()
        elif ch in [curses.KEY_PPAGE]:
            if start > 0:
                start -= maxy - 1
                if start < 0:
                    start = 0
                screen.clear()

        # to chapter
        elif ch in [curses.ascii.HT, curses.KEY_RIGHT, curses.KEY_LEFT]:
            if chaps[start + cursor_row][1]:
                soup = BeautifulSoup(fl.read(chaps[start + cursor_row][1]))
                chap = textify(
                    fl,
                    unicode(soup.find('body')).encode('utf-8'),
                    img_size=screen.getmaxyx()
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
                    chaps_pos[cursor_row]:chaps_pos[cursor_row]+maxy
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
                if ch == curses.ascii.ESC:
                    return
                try:
                   if chr(ch) == 'q':
                       return
                except:
                    pass

                # to TOC
                if ch in [curses.ascii.HT, curses.KEY_RIGHT, curses.KEY_LEFT]:
                    screen.clear()
                    break

                # up/down page
                elif ch in [curses.KEY_DOWN]:
                    if chaps_pos[cursor_row] + maxy - 1 < len(chap):
                        chaps_pos[cursor_row] += maxy - 1
                        screen.clear()
                elif ch in [curses.KEY_UP]:
                    if chaps_pos[cursor_row] > 0:
                        chaps_pos[cursor_row] -= maxy - 1
                        if chaps_pos[cursor_row] < 0:
                            chaps_pos[cursor_row] = 0
                        screen.clear()

                # up/down line
                elif ch in [curses.KEY_NPAGE]:
                    if chaps_pos[cursor_row] + maxy - 1 < len(chap):
                        chaps_pos[cursor_row] += 1
                        screen.clear()
                elif ch in [curses.KEY_PPAGE]:
                    if chaps_pos[cursor_row] > 0:
                        chaps_pos[cursor_row] -= 1
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
                                open_image(img, fl.read(img))
                    except (ValueError, IndexError):
                        pass

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument('-d', '--dump', action='store_true',
                        help='dump EPUB to text')
    parser.add_argument('EPUB', help='view EPUB')
    args = parser.parse_args()

    if args.EPUB:
        if args.dump:
            dump_epub(args.EPUB)
        else:
            try:
                curses.wrapper(curses_epub, args.EPUB)
            except KeyboardInterrupt:
                pass
