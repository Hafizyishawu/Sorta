import os

from sorta.extension_mapper import ExtensionMapper


def test_known_extensions_map_to_categories():
    assert ExtensionMapper.get_category('.mp3') == 'audio'
    assert ExtensionMapper.get_category('.MP4') == 'video'
    assert ExtensionMapper.get_category('.pdf') == 'pdf'


def test_document_subtypes_split_into_own_categories():
    assert ExtensionMapper.get_category('.docx') == 'word'
    assert ExtensionMapper.get_category('.xlsx') == 'spreadsheet'
    assert ExtensionMapper.get_category('.csv') == 'spreadsheet'
    assert ExtensionMapper.get_category('.pptx') == 'presentation'
    assert ExtensionMapper.get_category('.txt') == 'text'
    assert ExtensionMapper.get_category('.md') == 'text'
    assert ExtensionMapper.get_category('.epub') == 'ebook'


def test_newly_added_extensions_are_captured():
    assert ExtensionMapper.get_category('.webp') == 'image'
    assert ExtensionMapper.get_category('.heic') == 'image'
    assert ExtensionMapper.get_category('.m4a') == 'audio'
    assert ExtensionMapper.get_category('.webm') == 'video'
    assert ExtensionMapper.get_category('.html') == 'web'
    assert ExtensionMapper.get_category('.css') == 'web'
    assert ExtensionMapper.get_category('.zip') == 'archive'
    assert ExtensionMapper.get_category('.tar') == 'archive'


def test_web_and_archive_have_top_level_folders():
    assert ExtensionMapper.get_folder('web') == 'Web'
    assert ExtensionMapper.get_folder('archive') == 'Archives'


def test_unknown_extension_is_other():
    assert ExtensionMapper.get_category('.xyz') == 'other'


def test_folder_names_are_human_friendly():
    assert ExtensionMapper.get_folder('audio') == 'Audio'
    assert ExtensionMapper.get_folder('app') == 'Applications'
    assert ExtensionMapper.get_folder('setup') == 'Installers'


def test_document_subtypes_nest_under_documents():
    assert ExtensionMapper.get_folder('word') == os.path.join('Documents', 'Word')
    assert ExtensionMapper.get_folder('spreadsheet') == os.path.join('Documents', 'Spreadsheets')
    assert ExtensionMapper.get_folder('presentation') == os.path.join('Documents', 'Presentations')
    assert ExtensionMapper.get_folder('pdf') == os.path.join('Documents', 'PDF')
    assert ExtensionMapper.get_folder('text') == os.path.join('Documents', 'Text')
    assert ExtensionMapper.get_folder('ebook') == os.path.join('Documents', 'Ebooks')


def test_folder_name_falls_back_to_capitalized_category():
    assert ExtensionMapper.get_folder('other') == 'Other'
