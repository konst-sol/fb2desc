#!/usr/bin/env python3
# -*- mode: python; coding: utf-8; -*-
# (c) Con Radchenko mailto:lankier@gmail.com
#
# $Id: fb2desc.py,v 1.10 2008/09/15 04:18:45 con Exp con $
#

import sys, os
#import locale
import argparse
import codecs
import zipfile
from io import TextIOWrapper
import xml.etree.ElementTree as ET
import shutil
import textwrap
import re
import traceback

DEFAULT_COVER_IMAGE_VIEWER = 'feh'

def print_err(*args):
    print(*args, file=sys.stderr)

##----------------------------------------------------------------------

def natural_sort_key(s):
    # Splits a string into text and numbers
    # "a10" -> ['a', 10]
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s.strip())]

def replace_chars(s):
    return (s
            .replace('–', '--')
            .replace('—', '---')
            .replace('\xa0', ' ') # неразрывный пробел
            .replace('…', '...')
            .replace('«', '<<')
            .replace('»', '>>')
            .replace('“', '``')
            .replace('”', "''")
            .replace('„', ',,')
            )

def translit(s):
    trans_tbl = {
        'а': 'a',
        'б': 'b',
        'в': 'v',
        'г': 'g',
        'д': 'd',
        'е': 'e',
        'ё': 'yo',
        'ж': 'zh',
        'з': 'z',
        'и': 'i',
        'й': 'y',
        'к': 'k',
        'л': 'l',
        'м': 'm',
        'н': 'n',
        'о': 'o',
        'п': 'p',
        'р': 'r',
        'с': 's',
        'т': 't',
        'у': 'u',
        'ф': 'f',
        'х': 'h',
        'ц': 'c',
        'ч': 'ch',
        'ш': 'sh',
        'щ': 'sh',
        'ъ': '',
        'ы': 'y',
        'ь': '',
        'э': 'e',
        'ю': 'ju',
        'я': 'ya',
    }
    trans_table = str.maketrans(trans_tbl)
    s = s.lower()
    s = s.translate(trans_table)
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s


##----------------------------------------------------------------------

class FB2Info:
    def __init__(self, filename, zip_filename, file_obj, first_line, file_size):
        self.filename = filename
        self.zip_filename = zip_filename
        self.file_obj = file_obj
        if options.charset:
            self.file_obj = TextIOWrapper(file_obj, encoding=options.charset,
                                          errors='ignore')
        self.first_line = first_line
        self.file_size = file_size

        self.encoding = ''
        # b'<?xml version="1.0" encoding="UTF-8"?>\r\n'
        matchobj = re.search(rb'encoding=["\']([^"\']+)["\']', first_line)
        if matchobj:
            self.encoding = matchobj.group(1).decode('utf-8')

        #
        self.authors_list = []
        self.title = ''
        self.sequence_name = ''
        self.sequence_number = ''
        self.authors = ''
        self.annotation = ''

        self.desc = []
        self.cover = ''
        self.cover_name = ''
        self.cover_content_type = ''
        self.content = []
        self.tree = []

    def get_filename(self):
        '''Форматы:
        1 - "полные имена авторов, разделенные запятой - название (серия #номер)"
        2 - то же, но преобразованное в транслит и с заменой пробелов
        3 - "фамилии авторов, разделенные запятой - название"
        4 - то же, но преобразованное в транслит и с заменой пробелов
        5 - "первая буква автора в нижнем регистре/авторы, разделенные запятой, в нижнем регистре/авторы, разделенные запятой - название (серия #номер)"
        6 - то же, но преобразованное в транслит и с заменой пробелов
        '''
        format = options.fn_format

        authors = []
        full_authors = []
        for a in self.authors_list:
            if a[0]:
                authors.append(a[0])
            fa = ' '.join(i for i in a if i)
            if fa:
                full_authors.append(fa)
        authors = ', '.join(authors) or 'unknown'
        full_authors = ', '.join(full_authors) or 'unknown'
        title = self.title or 'unknown'

        seq = ''
        if self.sequence_name:
            if self.sequence_number:
                seq = f'{self.sequence_name} #{self.sequence_number}'
            else:
                seq = self.sequence_name

        if format == 3:
            out = f'{authors} - {title}'
        else:
            out = f'{full_authors} - {title}'
            if seq:
                out += f' ({seq})'

        if format in (2, 4, 6):
            out = translit(out)
            full_authors = translit(full_authors)

        #out = out.replace('/', '%').replace('\0', '').replace('?', '')
        for c in '|\\?*<":>+[]/':           # invalid chars in VFAT
            out = out.replace(c, '')
            if format in (4, 5):
                full_authors = full_authors.replace(c, '')

        fn_max = 240
        if format in (5, 6):
            fl = full_authors[0]
            if not fl.isalpha():
                fl = full_authors[1] # FIXME
            out = os.path.join(fl.lower(), full_authors.lower(), out[:fn_max])
        else:
            out = out[:fn_max]

        return out

    def format(self, format='pretty'):
        ann = []
        title = ''
        authors_list = []
        # [last-name, first-name, middle-name, nick-name]
        author_name = [None, None, None, None]
        genres = []
        sequence_name = ''
        sequence_number = ''
        for elem, data in self.desc:
            # data = data.strip()
            # if not data:
            #     continue
            if elem.startswith('/description/title-info/annotation/'):
                if not elem.endswith('href'):
                    ann.append(data)
                if elem.endswith(('/p', '/v', '/text-author')):
                    ann.append('\n')
            elif elem == '/description/title-info/book-title':
                title = data
            elif elem == '/description/title-info/author/first-name':
                author_name[1] = data
            elif elem == '/description/title-info/author/middle-name':
                author_name[2] = data
            elif elem == '/description/title-info/author/last-name':
                author_name[0] = data
                authors_list.append(author_name)
                author_name = [None, None, None, None]
            elif elem == '/description/title-info/author/nick-name':
                #author_name[3] = data
                if not author_name[0]:
                    author_name[0] = data
                else:
                    author_name[3] = data
                authors_list.append(author_name)
                author_name = [None, None, None, None]
            elif elem == '/description/title-info/genre':
                genres.append(data)
            elif elem == '/description/title-info/sequence/name':
                sequence_name = data
            elif elem == '/description/title-info/sequence/number':
                sequence_number = data

        self.authors_list = authors_list
        self.title = title
        self.sequence_name = sequence_name
        self.sequence_number = sequence_number

        ##authors_list.sort()
        authors = ', '.join(' '.join(n for n in a if n) for a in authors_list if a)
        self.authors = authors

        annotation = []
        ann = ''.join(ann).split('\n')
        for s in ann:
            s = '\n'.join(textwrap.wrap(s, width=72, break_long_words=False,
                                        initial_indent='  '))
            annotation.append(s)
        annotation = '\n'.join(annotation)
        if annotation:
            annotation = '\n' + annotation.rstrip()
        self.annotation = annotation


        if format == 'single':
            if sequence_name and sequence_number:
                out = f'{authors} - {title} ({sequence_name} {sequence_number})'
            elif sequence_name:
                out = f'{authors} - {title} ({sequence_name})'
            else:
                out = f'{authors} - {title}'
            #out = '%s: %s' % (filename, out)
            if options.replace: out = replace_chars(out)
            return out

        elif format == 'pretty':
            def add_col(name, value):
                if value:
                    out.append(f'{name:<13}: {value}')
            out = []
            add_col('File', self.filename)
            add_col('Zip Filename', self.zip_filename)
            add_col('Size', f'{self.file_size//1024} kb')
            add_col('Encoding', self.encoding)

            add_col('Author(s)', authors)
            add_col('Title', title)
            add_col('Genres', ', '.join(genres))
            if sequence_name:
                if sequence_number:
                    sequence = f'{sequence_name} ({sequence_number})'
                else:
                    sequence = sequence_name
                add_col('Sequence', sequence)
            add_col('Annotation', annotation)
            out.append('')
            out = '\n'.join(out)
            if options.replace: out = replace_chars(out)
            return out

        elif format == 'filename':
            return self.get_filename()

    def raw_format(self):
        if options.quiet:
            out = ''
        else:
            out = f'filename: {self.filename}\n'
            if self.zip_filename:
                out += f'zipfilename: {self.zip_filename}\n'
        for elem, data in self.desc:
            if not data:
                continue
            t = list(filter(elem.startswith, options.elements))
            #t = [x for x in options.elements if elem.startswith(x)]
            if options.elements == [] or t:
                out += f'{elem}: {data}\n'
        if options.replace: out = replace_chars(out)
        return out

    def show_cover(self):
        if not self.cover:
            print_err(f'{self.filename}: sorry, cover not found')
            return
        import base64, tempfile
        data = base64.b64decode(self.cover)
        if self.cover_content_type and self.cover_content_type.startswith('image/'):
            suffix = '.'+self.cover_content_type[6:]
        else:
            suffix = ''
        tmp_id, tmp_file = tempfile.mkstemp(suffix)
        try:
            open(tmp_file, 'wb').write(data)
            os.system(options.image_viewer+' '+tmp_file)
        finally:
            os.close(tmp_id)
            os.remove(tmp_file)

    def show_content(self):
        for secttion_level, data in self.content:
            if options.replace: data = replace_chars(data)
            print('  '*secttion_level+data)
        print()

    def rename(self):
        to = self.format('filename')
        to += options.suffix
        if options.dest_dir:
            to = os.path.join(options.dest_dir, to)
        to = os.path.abspath(to)
        if os.path.exists(to):
            print_err(f'file {to} already exists')
            return
        if not options.quiet:
            action = 'symlink' if options.slink else 'copy' if options.copy else 'rename'
            print(f'{action}: {self.filename} -> {to}')
        dir_name = os.path.dirname(to)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        if options.slink:
            os.symlink(self.filename, to)
            return
        elif options.copy:
            shutil.copy(self.filename, to)
            return
        os.rename(self.filename, to)

    def parse(self):
        if not self.first_line.startswith((b'<?xml', b'\xef\xbb\xbf<?xml')):
            print_err(f'Warning: file {self.filename} is not an XML file. Skipped.')
            print(self.first_line[:5])
            #shutil.copy(filename, '/home/con/t/')
            return

        self.parse_xml()

        if options.rename:
            self.rename()
            return
        if options.show_tree:
            for e, n in self.tree:
                if n > 1:
                    print(f'{e} [{n}]')
                else:
                    print(e)
            return

        if options.format == 'pretty':
            print(self.format('pretty'))
        elif options.format == 'filename':
            print(self.format('filename'))
        elif options.format == 'single':
            print(self.format('single'))
        elif (options.format == ''
              and not options.show_cover
              and not options.show_content):
            print(self.raw_format())
        if options.show_cover or options.show_content:
            if options.format == 'raw':
                print(self.raw_format())
            if options.show_content:
                self.show_content()
            if options.show_cover:
                self.show_cover()

    def parse_xml(self):
        elem_stack = []
        is_desc = False
        is_title = False
        cur_title = []
        is_par = False
        cur_par = ''
        section_level = 0

        context = ET.iterparse(self.file_obj, events=('start', 'end'))
        if not next(context)[1].tag.endswith('FictionBook'):
            raise ValueError('not FB2')

        for event, elem in context:
            if elem.tag.startswith('{'):
                elem.tag = elem.tag.split('}', 1)[1]
            if event == 'start':
                if is_par:
                    continue
                if elem.tag == 'p':
                    is_par = True
                    cur_par = ''
                    if elem.text and elem.text.strip():
                        cur_par = elem.text

                if elem.tag == 'description': is_desc = True
                if elem.tag == 'section': section_level += 1

                if is_desc or options.show_tree:
                    elem_stack.append(elem.tag)
                    elem_name = f'/{"/".join(elem_stack)}'
                    if options.show_tree:
                        if self.tree and self.tree[-1][0] == elem_name:
                            self.tree[-1][1] += 1
                        else: #if not elem.endswith('/p') and not elem.endswith('/v'):
                            self.tree.append([elem_name, 1])
                    for name, value in elem.attrib.items():
                        if name.startswith('{'):
                            name = name.split('}', 1)[1]
                        self.desc.append((f'{elem_name}/{name}', value))
                        if (elem_name == '/description/title-info/coverpage/image'
                            and name.endswith('href')):
                            self.cover_name = value[1:]

                if options.show_content and elem.tag == 'title':
                    is_title = True
                    cur_title = []


            elif event == 'end':
                text = ''
                if elem.text and elem.text.strip():
                    text = elem.text
                tail = ''
                if elem.tail and elem.tail.strip():
                    tail = elem.tail
                if elem.tag == 'p':
                    is_par = False
                    if tail:
                        cur_par += tail
                    text = ' '.join(cur_par.split())
                    elem_name = '/'+'/'.join(elem_stack)
                elif is_par:
                    cur_par += text
                    cur_par += tail
                    continue

                if is_desc:
                    if text:
                        elem_name = '/'+'/'.join(elem_stack)
                        self.desc.append((elem_name, text))
                    if tail:
                        elem_name = '/'+'/'.join(elem_stack[:-1])
                        self.desc.append((elem_name, tail))

                if is_desc or options.show_tree:
                    del elem_stack[-1]

                if options.show_content:
                    if elem.tag == 'title':
                        is_title = False
                        self.content.append((section_level, ' '.join(cur_title)))
                    elif is_title:
                        if text: cur_title.append(text)
                        if tail: cur_title.append(tail)

                if (options.show_cover
                    and elem.tag == 'binary'
                    and elem.attrib.get('id') == self.cover_name):
                    self.cover = elem.text
                    self.cover_content_type = elem.attrib.get('content-type', '')

                if elem.tag == 'section': section_level -= 1
                if elem.tag == 'description':
                    if (not options.show_cover
                        and not options.show_content
                        and not options.show_tree):
                        break
                    else:
                        is_desc = False



##----------------------------------------------------------------------

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print_err(f'{self.prog}: error: {message}')
        print_err("Try '--help' for more information.")
        sys.exit(2)

def parse_args():
    global options

    parser = CustomArgumentParser(
        description='show description of FB2 file(s)')

    parser.add_argument('file', nargs='+', help='files or dirs')

    parser.add_argument('-w', '--raw-format', action='store_true',
                        help='output in raw format')
    parser.add_argument('-p', '--pretty', action='store_true',
                        help='output in pretty format')
    parser.add_argument('-l', '--single', action='store_true',
                        help='output in single format')
    parser.add_argument('--output', dest='format',
                        choices=['raw', 'pretty', 'single', 'filename'],
                        default='', help='output format')
    parser.add_argument('-o', '--contents', dest='show_content', action='store_true',
                        help='show table of contents')
    parser.add_argument('-t', '--tree', dest='show_tree', action='store_true',
                        help='show XML tree')
    parser.add_argument('-v', '--cover', dest='show_cover', action='store_true',
                        help='show cover')
    parser.add_argument('-c', '--charset',
                        help='use <CHARSET> for FB2 files')
    parser.add_argument('-z', '--zip-charset', metavar='CHARSET',
                        help='use <CHARSET> for zipped filenames')
    parser.add_argument('-r', '--replace', action='store_true',
                        help='replace chars for 8-bit encodings')
    parser.add_argument('-e', '--elements', default=[],
                        help='show only this elements (comma separeted)')
    parser.add_argument('-R', '--rename', action='store_true', help='rename mode')
    parser.add_argument('-S', '--slink', action='store_true',
                        help='create softlinks instead of renaming')
    parser.add_argument('-C', '--copy', action='store_true',
                        help='copy files instead of renaming')
    parser.add_argument('--fn-format', type=int, choices=(1, 2, 3, 4, 5, 6), default=2,
                        help='rename pattern; default: %(default)s')
    parser.add_argument('--dest-dir', help='destination dir for renamed files')
    parser.add_argument('--image-viewer', default=DEFAULT_COVER_IMAGE_VIEWER,
                        help='cover image viewer')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='suppress output filename in raw format')

    options = parser.parse_args()

    if options.raw_format:
        options.format = 'raw'
    if options.single:
        options.format = 'single'
    if options.pretty:
        options.format = 'pretty'
    if options.elements:
        options.elements = options.elements.split(',')
    if options.slink or options.copy:
        options.rename = True

    if options.charset:
        try:
            codecs.lookup(options.charset)
        except LookupError as err:
            sys.exit(f'{parser.prog}: error: {err}')
    if options.zip_charset:
        try:
            codecs.lookup(options.zip_charset)
        except LookupError as err:
            sys.exit(f'{parser.prog}: error: {err}')

    options.suffix = None

##----------------------------------------------------------------------

def yield_fb2(raw_filename):
    filename = os.path.abspath(raw_filename)
    if zipfile.is_zipfile(raw_filename):
        options.suffix = '.fb2.zip'
        with zipfile.ZipFile(raw_filename, metadata_encoding=options.zip_charset) as archive:
            for file_info in archive.infolist():
                if file_info.is_dir():
                    continue
                fileobj = archive.open(file_info)
                first_line = fileobj.readline()
                fileobj.seek(0)
                yield (filename, file_info.filename, fileobj,
                       first_line, file_info.file_size)
                if options.rename:
                    return
    else:
        fileobj = open(raw_filename, 'rb')
        first_line = fileobj.readline()
        if first_line.startswith(b'7z\xbc\xaf\x27\x1c'):
            fileobj.close()
            try:
                import py7zr
            except ModuleNotFoundError:
                print_err('ModuleNotFoundError: py7zr')
                return
            options.suffix ='.fb2.7z'
            with py7zr.SevenZipFile(raw_filename) as archive:
                info_list = {}
                for file_info in archive.list():
                    if file_info.is_directory: continue
                    info_list[file_info.filename] = file_info.uncompressed
                for zip_filename, fileobj in archive.readall().items():
                    #if filename.endswith('/'): continue
                    first_line = fileobj.readline()
                    fileobj.seek(0)
                    file_size = info_list[zip_filename]
                    yield (filename, zip_filename, fileobj, first_line, file_size)
                    if options.rename:
                        return

        else:
            options.suffix = '.fb2'
            fileobj.seek(0)
            yield (filename, None, fileobj, first_line, os.path.getsize(filename))

##----------------------------------------------------------------------

def main():
    parse_args()
    #print(options)

    in_files = []
    for fn in options.file:
        if os.path.isdir(fn):
            for root, dirs, files in os.walk(fn):
                for f in files:
                    in_files.append(os.path.join(root, f))
        else:
            in_files.append(fn)

    in_files.sort(key=natural_sort_key)
    #print(in_files)

    for filename in in_files:
        if not os.path.isfile(filename):
            print_err(f"ERROR: file not found: '{filename}'")
            continue

        try:
            for info in yield_fb2(filename):
                fb2 = FB2Info(*info)
                fb2.parse()
        except Exception:
            print_err('>>', filename)
            traceback.print_exc()
            ##shutil.copy(raw_filename, '/home/con/t/')


if __name__ == '__main__':
    main()

# end
