from sorta.extension_mapper import ExtensionMapper


def test_known_extensions_map_to_categories():
    assert ExtensionMapper.get_category('.mp3') == 'audio'
    assert ExtensionMapper.get_category('.MP4') == 'video'
    assert ExtensionMapper.get_category('.pdf') == 'document'


def test_unknown_extension_is_other():
    assert ExtensionMapper.get_category('.xyz') == 'other'


def test_folder_names_are_human_friendly():
    assert ExtensionMapper.get_folder('audio') == 'Audio'
    assert ExtensionMapper.get_folder('app') == 'Applications'
    assert ExtensionMapper.get_folder('setup') == 'Installers'


def test_folder_name_falls_back_to_capitalized_category():
    assert ExtensionMapper.get_folder('other') == 'Other'
