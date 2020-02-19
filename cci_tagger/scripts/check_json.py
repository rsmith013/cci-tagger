# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '19 Feb 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'


import argparse
import json

parser = argparse.ArgumentParser(description='Check whether a given JSON file matches the expected format'
                                             'to be used with the CCI tagger')

parser.add_argument('json_file', help='JSON file to test')

args = parser.parse_args()

class TestJSONFile:

    REQUIRED_KEYS = {'datasets'}
    ACCEPTABLE_KEYS = {'datasets', 'filters', 'mappings', 'defaults', 'realisations', 'overrides'}
    FILTER_KEYS = {'pattern','realisation'}

    def __init__(self, file):
        self.file = file
        self.data = None

    def _read_file(self):
        with open(self.file) as reader:
            data = json.load(reader)
        return data

    def test_json_formatting(self):
        """
        Check whether file will load as correct JSON
        """
        try:
            self._read_file()
        except Exception as e:
            print(f'ERROR: File format error - {e}')

    def test_json_keys(self):
        """
        Checks the top level keys and evaluates:
        - JSON file has all required keys
        - All keys are valid keys
        """
        keys_in_file = set(self.data.keys())

        # Check required key
        if not keys_in_file.issuperset(self.REQUIRED_KEYS):
            print(f'ERROR: Required keys {self.REQUIRED_KEYS} not present')

        # Check for invalid keys
        unacceptable_keys = keys_in_file.difference(self.ACCEPTABLE_KEYS)
        if unacceptable_keys:
            print(f'WARNING: Invalid sections. {unacceptable_keys} are not valid section keys')

    def test_datasets(self):
        """
        Checks that the datasets key and evaluates:
        - Datasets key returns a list
        - There is at least 1 dataset
        - Dataset values are strings
        """
        datasets = self.data.get('datasets')

        if datasets is None:
            return

        # Check datasets key returns a list
        is_list = isinstance(datasets,list)
        if not is_list:
            print(f'ERROR: Invalid datasets. Dataset key should return a list')
            return

        # Check for at least one dataset
        if not datasets:
            print(f'ERROR: There should be at least 1 dataset')

        # Check datasets are strings
        for dataset in datasets:
            if not isinstance(dataset, str):
                print(f'ERROR: Datasets should be strings. {dataset} is not a string')

    def test_filters(self):
        """
        Checks that the filters key and evaluates:
         - Key returns a dict
         - Dataset filters match datasets listed
         - The dataset filters are a list of dicts
         - The dataset filters include the keys 'pattern' and 'realisation'
        """

        filters = self.data.get('filters')
        if filters is None:
            return

        # Test key returns a dict
        is_dict = isinstance(filters, dict)
        if not is_dict:
            print(f'ERROR: Filters object should be a dict')
            return

        # Test datasets match datasets listed
        filter_datasets = set(filters.keys())
        root_datasets = set(self.data.get('datasets',{}))

        if not filter_datasets.issubset(root_datasets):
            diff = filter_datasets.difference(root_datasets)
            print(f'ERROR: Unexpected dataset. Filters should match to a dataset specified in datasets section. {diff} does not match')

        # Test filters are list of dicts
        for ds, filters in filters.items():

            is_list = isinstance(filters, list)
            if not is_list:
                print('ERROR: Dataset filter should be a list. eg.')
                print('\t{'
                      '\n\t\t "filters": {'
                      '\n\t\t\t"/path/to/dataset": []'
                      '\n\t\t}'
                      '\n\t}')
                return

            # Test dataset filters include required keys
            for filter in filters:
                filter_keys = set(filter.keys())

                if not filter_keys.issuperset(self.FILTER_KEYS):
                    diff = self.FILTER_KEYS.difference(filter_keys)
                    print(f'ERROR: Missing required keys {diff}')

                diff = filter_keys.difference(self.FILTER_KEYS)
                if diff:
                    print(f'WARNING: Unexpected keys. {diff} will be ignored')


    def test_mappings(self):
        """
        Checks mappings key and evaluates:
        - Checks all the keys listed are valid
        """
        mappings = self.data.get('mappings')
        if mappings is None:
            return

    def test_defaults(self):
        """
        Checks the defaults key and evaluates:
        - Checks all the keys listed are valid
        - Checks values are strings
        """
        defaults = self.data.get('defaults')
        if defaults is None:
            return

    def test_realisations(self):
        """
        Checks the realisations key and evaluates:
        - All datasets listed are in the datasets key
        """
        realisations = self.data.get('realisations')
        if realisations is None:
            return

    def test_overrides(self):
        """
        Checks the overrides section and evaluates:
        - All the keys listed are valid
        - All the key values are lists
        """
        overrides = self.data.get('overrides')
        if overrides is None:
            return

    def run(self):

        try:
            self.test_json_formatting()
        except Exception:
            print('CRITICAL: The file cannot be read so no other tests will work')
            exit(1)

        # Load the data
        self.data = self._read_file()

        # Run the tests
        self.test_json_keys()
        self.test_datasets()
        self.test_filters()
        self.test_mappings()
        self.test_defaults()
        self.test_realisations()
        self.test_overrides()

