"""Module holding some utilities for doing file related stuff"""

import os.path
import re
import json
from collections import defaultdict

CANONICAL_NAMES_FILE = '../../data/test_segment_names.json'

CANONICAL_FOLDERS = ('Dog_1', 'Dog_2', 'Dog_3',
                     'Dog_4', 'Dog_5',
                     'Patient_1',
                     'Patient_2')



def get_segment_name(name):
    """Returns the canonical segment name for a string *name*. The canonical
    segment name is the one identifying the original matlab data file and will
    be inferred by the prefix of the basename using a regular expression. If the
    name can't be matched, the argument is returned."""

    pattern = r"([DP][a-z]*_[1-5]_[a-z]*_segment_[0-9]{4}).*"
    basename = os.path.basename(name)  # Remove any directories from the name
    match = re.match(pattern, basename)
    if match is None:
        return name
    else:
        return match.group(1) + '.mat'


def get_subject(string):
    """Extracts the subject string from the given string. The string must contain a substring matching a canonical folder name. If the string doesn't contain a subject, None is returned"""
    subject_pattern = r".*(Patient_[12]|Dog_[1-5]).*"
    subject = re.match(subject_pattern, string)
    if subject is not None:
        return subject.group(1)
    else:
        return None


def generate_canonical_names(name_file=CANONICAL_NAMES_FILE):
    """
    Generates a json file containing all the canonical test file names. The file is saved to the path denoted by the module constant CANONICAL_NAMES_FILE'
    """
    import subprocess
    filenames = subprocess.check_output(['find', '../../data/', '-name', '*test*.mat']).split()
    decoded = [os.path.basename(name.decode()) for name in filenames]
    matched_names = [re.match(r"([DP][a-z]*_[1-5]_[a-z]*_segment_[0-9]{4}).*", name) for name in decoded]
    only_matches = [match.group(1) for match in matched_names if match]
    only_matches.sort()
    formatted_names = ["{}.mat".format(name) for name in only_matches]
    with open(name_file, 'w') as fp:
        json.dump(formatted_names, fp, indent=4, separators=(',', ': '))
    return set(formatted_names)


def load_canonical_names(name_file=CANONICAL_NAMES_FILE):
    """Loads the canonical names as a set of names"""
    try:
        with open(name_file, 'r') as fp:
            names = json.load(fp)
            return set(names)
    except FileNotFoundError:
        return generate_canonical_names(name_file)


def expand_paths(filenames, recursive=True):
    """Goes through the list of *filenames* and expands any directory to the files included in that directory.
    If *recursive* is True, any directories in the base directories will be expanded as well. If *recursive* is
    False, only normal files in the directories will be included.
    The returned list only includes non-directory files."""
    new_files = []
    for file in filenames:
        if os.path.isdir(file):
            if recursive:
                #We recurse over all files contained in the directory and add them to the list of files
                for dirpath, _, subfilenames in os.walk(file):
                    new_files.extend([os.path.join(dirpath, filename)
                                      for filename in subfilenames])
            else:
                #No recursion, we just do a listfile on the files of any directoy in filenames
                for subfile in os.listdir(file):
                    if os.path.isfile(subfile):
                        new_files.append(os.path.join(file, subfile))
        elif os.path.isfile(file):
            new_files.append(file)
    return new_files


def expand_folders(feature_folders, canonical_folders=CANONICAL_FOLDERS):
    """Goes through the list of *feature_folders* and replcaes any directory which contains the canonical subject folders with the path to those folders. Folders not containing any canonical feature folder is left as is.
    """
    canonical_folders = set(canonical_folders)
    new_folders = []
    for folder in feature_folders:
        subfolders = set([sf for sf in os.listdir(folder) if os.path.isdir(os.path.join(folder, sf))])

        common_folders = subfolders & canonical_folders
        if common_folders:
            new_folders.extend([os.path.join(folder, common)
                                for common
                                in common_folders])
        else:
            new_folders.append(folder)
    return new_folders


def group_folders(feature_folders):
    """
    Groups the feature folder per subject. Returns a dictionary with subject to
    feature folders lists. If the subject of any of the folders can't be found,
    it will be excluded from the grouping.
    """

    grouped_folders = defaultdict(list)
    for feature_folder in feature_folders:
        subject = get_subject(feature_folder)
        if subject is not None:
            grouped_folders[subject].append(feature_folder)
    return grouped_folders


def load_modules(module_names):
    """Loads the give list of python files as modules and returns the list of module objects."""
    import imp

    modules = []
    for filename in module_names:
        modname = os.path.basename(filename)
        mod = imp.load_source(modname, filename)
        modules.append(mod)
    return modules


def get_class_files(dirname, class_name):
    """
    Return the filenames in directory *dirname*, which are of the class *class_name*.
    """
    all_files = expand_paths([dirname])
    return [filename for filename in all_files
            if '.mat' in filename and class_name in filename]


def get_preictal_files(dirname):
    """
    Returns all .mat files in the directory which correspond to preictal segments.
    """
    return get_class_files(dirname, 'preictal')



def get_interictal_files(dirname):
    """
    Returns all .mat files in the directory which correspond to interictal segments.
    """
    return get_class_files(dirname, 'interictal')


def get_test_files(dirname):
    """
    Returns all .mat files in the directory which correspond to test segments.
    """
    return get_class_files(dirname, 'test')


def process_segments(files, fun, output_format="{basename}_{fun_name}.txt"):
    """Loads each of the files in the list *files* as segments and applies the function *fun* to each of the segment.
    The function *fun* should return an iteration of rows which will be written to files using the given output_format.
     *basename* will be the name of the files without extension, *fun_name* is the __name__ attribute of the function
     object.
    """
    import segment

    for file in files:
        seg = segment.Segment(file)
        fun_name = fun.__name__
        base_name, ext = os.path.splitext(file)
        output_name = output_format.format(base_name=base_name, fun_name=fun_name)
        with open(output_name, 'w') as fp:
            fp.writelines(fun(seg))
