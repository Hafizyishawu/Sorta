import os
from typing import List, Dict
from .extension_mapper import ExtensionMapper

class FileOrganizer:
    """
    Suggests organization actions for files based on their type/category.
    """
    def __init__(self, files_metadata: List[Dict], base_dir: str):
        self.files_metadata = files_metadata
        self.base_dir = base_dir

    def _category_target_base(self, category):
        # Anchor the category folder to base_dir, but collapse any leading parts
        # that base_dir already represents. Running inside ~/Documents must reuse
        # that folder as the single "Documents" parent (-> ~/Documents/Word)
        # rather than nesting another like-named folder (~/Documents/Documents/
        # Word). Without this, repeated runs stack Documents/Documents/Documents.
        rel_parts = ExtensionMapper.get_folder(category).split(os.sep)
        base_name = os.path.basename(os.path.normpath(self.base_dir))
        while rel_parts and rel_parts[0].lower() == base_name.lower():
            rel_parts.pop(0)
        if not rel_parts:
            return self.base_dir
        return os.path.join(self.base_dir, *rel_parts)

    def _longest_common_prefix(self, strings):
        if not strings:
            return ''
        s1 = min(strings)
        s2 = max(strings)
        for i, c in enumerate(s1):
            if i >= len(s2) or c != s2[i]:
                return s1[:i]
        return s1

    def get_organization_suggestions(self) -> List[Dict]:
        suggestions = []
        # Group root-level files by category
        files_by_category = {}
        for file in self.files_metadata:
            ext = file['extension']
            category = ExtensionMapper.get_category(ext)
            if category == 'other':
                continue
            parent_folder = os.path.dirname(os.path.abspath(file['path']))
            if os.path.abspath(parent_folder) != os.path.abspath(self.base_dir):
                continue
            files_by_category.setdefault(category, []).append(file)

        for category, files in files_by_category.items():
            # Group files with similar names (prefix before first non-alnum/underscore/dash or digit sequence)
            import re
            def base_name(f):
                name = os.path.splitext(os.path.basename(f['path']))[0]
                # Remove trailing digits and separators
                return re.sub(r'([\W_\-]?\d+)+$', '', name)
            groups = {}
            for file in files:
                prefix = base_name(file)
                groups.setdefault(prefix, []).append(file)
            target_folder_base = self._category_target_base(category)
            for prefix, group_files in groups.items():
                # Only nest into a name-prefix subfolder when more than one file
                # shares that prefix. A lone file goes straight into the category
                # folder rather than a single-file subfolder.
                if prefix and len(group_files) > 1:
                    target_folder = os.path.join(target_folder_base, prefix)
                else:
                    target_folder = target_folder_base
                for file in group_files:
                    target_path = os.path.join(target_folder, os.path.basename(file['path']))
                    if os.path.abspath(file['path']) != os.path.abspath(target_path):
                        suggestions.append({
                            'source': file['path'],
                            'target': target_path,
                            'category': category,
                            'group': prefix or None
                        })
        return suggestions
