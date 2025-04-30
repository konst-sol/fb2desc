# fb2desc

A command-line utility for working with FB2 (FictionBook) files.

## Options

- `-w, --raw-format` - Output description in "raw" format (default)
- `-p, --pretty` - Output description in human-readable format
- `-l, --single` - Single-line output
- `--output format` - Output in specified format (raw, pretty, single, filename)
- `-o, --contents` - Show table of contents
- `-t, --tree` - Show XML tree
- `-v, --cover` - Show cover
- `-c, --charset <charset>` - Output encoding
- `-z, --zip-charset <charset>` - Encoding for filenames in ZIP archives
- `-r, --replace` - Replace certain characters (quotation marks, etc.)
- `-e, --elements <elements>` - Show only specified elements
- `-R, --rename` - Rename mode
- `-S, --slink` - Create softlinks instead of renaming
- `-C, --copy` - Copy instead of renaming
- `--dest-dir` - Directory for renamed files
- `--image-viewer` - Cover image viewer program
- `-q, --quiet` - Don't display filenames
- `-h, --help` - Display help information

## Usage Examples

### Default Usage

```bash
$ fb2desc.py example.fb2

filename: /home/user/example.fb2
/description/title-info/genre: history_russia
/description/title-info/genre: romance_historical
/description/title-info/genre: literature_classics
/description/title-info/genre: literature_history
/description/title-info/genre: literature_war
/description/title-info/genre: literature_rus_classsic
/description/title-info/genre: computers
/description/title-info/author/first-name: Лев
/description/title-info/author/middle-name: Николаевич
/description/title-info/author/last-name: Толстой
/description/title-info/book-title: Война и мир
[...]
```

### Show Human-Readable Description, Table of Contents, and Cover

```bash
$ fb2desc.py -pov example.fb2

File         : /home/user/example.fb2
Size         : 98 kb
Author(s)    : Толстой Лев Николаевич
Title        : Война и мир
Genres       : history_russia, romance_historical, literature_classics, literature_history, literature_war, literature_rus_classsic, computers
Sequence     : Детство, Отрочество, Юность (2)
Annotation   :
  Это тестовый файл FictionBook 2.0. Создан Грибовым Дмитрием в
демонстрационных целях и для экспериментов с библиотекой FIctionBook.lib.
К сожалению сам роман я в FB2 пока не перевел.
[...]

Название стиха
ТОМ 1
  ЧАСТЬ ПЕРВАЯ
    I
    Это пример глубоко вложенных частей
      Рыба (1.I)
      Рыба (1.II)
      Рыба (1.III)
      Рыба (1.IV)
        Рыба (1.IV.a)
        Рыба (1.IV.б)
        Рыба (1.IV.в)
[...]
```

### Show Only Specified Elements

```bash
$ fb2desc.py -e /description/title-info/author/first-name,/description/title-info/author/last-name,/description/title-info/book-title,/description/title-info/genre example.fb2

filename: /home/user/example.fb2
/description/title-info/genre: history_russia
/description/title-info/genre: romance_historical
/description/title-info/genre: literature_classics
/description/title-info/genre: literature_history
/description/title-info/genre: literature_war
/description/title-info/genre: literature_rus_classsic
/description/title-info/genre: computers
/description/title-info/author/first-name: Лев
/description/title-info/author/last-name: Толстой
/description/title-info/book-title: Война и мир
```

### Recursive Directory Traversal

```bash
fb2desc.py dir
```

## Rename Mode

The program can rename FB2 files according to predefined templates.
The command `fb2desc -R example.fb2` will rename example.fb2 to
`tolstoy_lev_nikolaevich_voyna_i_mir_detstvo_otrochestvo_junost_2.fb2`

You can specify a renaming template:

1. "full author names, comma-separated - title (series #number)"
2. Same as 1, but converted to transliteration with spaces replaced
3. "author surnames, comma-separated - title"
4. Same as 3, but converted to transliteration with spaces replaced
5. "first letter of author in lowercase/authors, comma-separated, in lowercase/authors, comma-separated - title (series #number)"
6. Same as 5, but converted to transliteration with spaces replaced

Template #2 is used by default.

### Renaming Template Example

```bash
fb2desc -R --fn-format 6 example.fb2
```

This will create a directory `t/tolstoy_lev_nikolaevich/` and rename the file to
`t/tolstoy_lev_nikolaevich/tolstoy_lev_nikolaevich_voyna_i_mir_detstvo_otrochestvo_junost_2.fb2`

Instead of renaming, you can copy the file:

```bash
fb2desc -C --fn-format 6 example.fb2
```

or create a softlink:

```bash
fb2desc -S example.fb2
```

If you specify a directory instead of a filename, the program will recursively traverse
directories and rename all found files.

In rename mode, you can specify a target directory.

### Example

Traverse all directories in `dir`, find FB2 files, and create symbolic links to them in the `~/books` directory:

```bash
fb2desc -S --dest-dir ~/books dir
```
