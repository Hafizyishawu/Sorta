import os


class ExtensionMapper:
    CATEGORY_MAP = {
        'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.aiff', '.opus', '.wma'],
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.webm', '.m4v', '.mpeg', '.mpg', '.flv', '.3gp'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff', '.tif', '.svg', '.ico'],
        'word': ['.doc', '.docx', '.odt', '.rtf', '.pages'],
        'spreadsheet': ['.xls', '.xlsx', '.csv', '.ods', '.numbers'],
        'presentation': ['.ppt', '.pptx', '.key', '.odp'],
        'pdf': ['.pdf'],
        'text': ['.txt', '.md'],
        'ebook': ['.epub', '.mobi', '.azw3'],
        'web': ['.html', '.htm', '.css', '.js'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'app': ['.app', '.exe', '.dmg', '.deb', '.rpm'],
        'setup': ['.msi', '.pkg', '.iso', '.dmg'],
    }

    # Folder paths are expressed as path-part tuples. Document sub-types nest
    # under a shared "Documents" parent so the destination tree groups them
    # together (Documents/Word, Documents/Spreadsheets, ...) while media and
    # apps stay at the top level.
    CATEGORY_FOLDERS = {
        'audio': ('Audio',),
        'video': ('Videos',),
        'image': ('Images',),
        'word': ('Documents', 'Word'),
        'spreadsheet': ('Documents', 'Spreadsheets'),
        'presentation': ('Documents', 'Presentations'),
        'pdf': ('Documents', 'PDF'),
        'text': ('Documents', 'Text'),
        'ebook': ('Documents', 'Ebooks'),
        'web': ('Web',),
        'archive': ('Archives',),
        'app': ('Applications',),
        'setup': ('Installers',),
    }

    DOCUMENT_CATEGORIES = ('word', 'spreadsheet', 'presentation', 'pdf', 'text', 'ebook')

    @classmethod
    def get_folder(cls, category: str) -> str:
        parts = cls.CATEGORY_FOLDERS.get(category, (category.capitalize(),))
        return os.path.join(*parts)

    @classmethod
    def get_category(cls, extension: str) -> str:
        for category, exts in cls.CATEGORY_MAP.items():
            if extension.lower() in exts:
                return category
        return 'other'

    @classmethod
    def all_categories(cls):
        return list(cls.CATEGORY_MAP.keys())
