class ExtensionMapper:
    CATEGORY_MAP = {
        'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg'],
        'video': ['.mp4', '.mov', '.avi', '.mkv', '.wmv'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
        'document': ['.doc', '.docx', '.pdf', '.txt', '.xls', '.xlsx'],
        'app': ['.app', '.exe', '.dmg', '.deb', '.rpm'],
        'setup': ['.msi', '.pkg', '.iso', '.dmg'],
    }

    CATEGORY_FOLDERS = {
        'audio': 'Audio',
        'video': 'Videos',
        'image': 'Images',
        'document': 'Documents',
        'app': 'Applications',
        'setup': 'Installers',
    }

    @classmethod
    def get_folder(cls, category: str) -> str:
        return cls.CATEGORY_FOLDERS.get(category, category.capitalize())

    @classmethod
    def get_category(cls, extension: str) -> str:
        for category, exts in cls.CATEGORY_MAP.items():
            if extension.lower() in exts:
                return category
        return 'other'

    @classmethod
    def all_categories(cls):
        return list(cls.CATEGORY_MAP.keys())
