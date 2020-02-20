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
from cci_tagger.conf.constants import DRS_FACETS


class TestJSONFile:

    REQUIRED_KEYS = {'datasets'}
    ACCEPTABLE_KEYS = {'datasets', 'filters', 'mappings', 'defaults', 'realisations', 'overrides'}
    FILTER_KEYS = {'pattern','realisation'}
    FACET_KEYS = set(DRS_FACETS)

    def __init__(self, file):
        self.file = file
        self.data = None

    def _read_file(self):
        with open(self.file) as reader:
            data = json.load(reader)
        return data

    def _check_type(self,label, object, expected):
        is_object = isinstance(object,expected)
        if not is_object:
            print(f'\t\tERROR: {label} object should be a {expected}. Got {type(object)} instead.')

        return is_object

    def _check_valid_keys(self, observed, expected):
        """
        Give some feedback on unexpected keys
        :param observed: Object which can be converted to set and provide list of observed values
        :param expected: Expected values
        """

        key_set = set(observed)

        diff = key_set.difference(expected)
        if diff:
            print(f'\t\tWARNING: Unexpected keys. {diff} will be ignored')

    def test_json_formatting(self):
        """
        Check whether file will load as correct JSON
        """
        try:
            self._read_file()
        except Exception as e:
            print(f'\t\tERROR: File format error - {e}')

    def test_json_keys(self):
        """
        Checks the top level keys and evaluates:
        - JSON file has all required keys
        - All keys are valid keys
        """
        keys_in_file = set(self.data.keys())

        # Check required key
        if not keys_in_file.issuperset(self.REQUIRED_KEYS):
            print(f'\t\tERROR: Required keys {self.REQUIRED_KEYS} not present')

        # Check for invalid keys
        unacceptable_keys = keys_in_file.difference(self.ACCEPTABLE_KEYS)
        if unacceptable_keys:
            print(f'\t\tWARNING: Invalid sections. {unacceptable_keys} are not valid section keys')

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
        if not self._check_type('Datasets', datasets, list):
            return

        # Check for at least one dataset
        if not datasets:
            print(f'\t\tERROR: There should be at least 1 dataset')

        # Check datasets are strings
        for dataset in datasets:
            if not isinstance(dataset, str):
                print(f'\t\tERROR: Datasets should be strings. {dataset} is not a string')

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
        if not self._check_type('Filters', filters, dict):
            return

        # Test datasets match datasets listed
        filter_datasets = set(filters.keys())
        root_datasets = set(self.data.get('datasets',{}))

        if not filter_datasets.issubset(root_datasets):
            diff = filter_datasets.difference(root_datasets)
            print(f'\t\tERROR: Unexpected dataset. Filters should match to a dataset specified in datasets section. {diff} does not match')

        # Test filters are list of dicts
        for ds, filters in filters.items():

            is_list = isinstance(filters, list)
            if not is_list:
                print('\t\tERROR: Dataset filter should be a list. eg.')
                print('\t\t\t{'
                      '\n\t\t\t\t "filters": {'
                      '\n\t\t\t\t\t"/path/to/dataset": []'
                      '\n\t\t\t\t}'
                      '\n\t\t\t}')
                return

            # Test dataset filters include required keys
            for filter in filters:
                filter_keys = set(filter.keys())

                if not filter_keys.issuperset(self.FILTER_KEYS):
                    diff = self.FILTER_KEYS.difference(filter_keys)
                    print(f'\t\tERROR: Missing required keys {diff}')

                diff = filter_keys.difference(self.FILTER_KEYS)
                if diff:
                    print(f'\t\tWARNING: Unexpected keys. {diff} will be ignored')


    def test_mappings(self):
        """
        Checks mappings key and evaluates:
        - Checks mapping section is dict
        - Checks all the keys listed are valid
        """
        mappings = self.data.get('mappings')
        if mappings is None:
            return

        # Check mapping section is dict
        if not self._check_type('Mappings', mappings, dict):
            return

        valid_mapping_keys = self.FACET_KEYS.union({'merged'})

        # Check all keys are valid
        self._check_valid_keys(mappings, valid_mapping_keys)

    def test_defaults(self):
        """
        Checks the defaults key and evaluates:
        - Check key returns a dictionary
        - Checks all the keys listed are valid
        - Checks values are strings
        """
        defaults = self.data.get('defaults')
        if defaults is None:
            return

        # Check key returns a dict
        if not self._check_type('Defaults', defaults, dict):
            return

        # Check keys are valid
        self._check_valid_keys(defaults, self.FACET_KEYS)

        # Check values are strings
        for default in defaults:
            if not isinstance(default, str):
                print(f'\t\tERROR: Defaults should be strings. {default} is not a string')


    def test_realisations(self):
        """
        Checks the realisations key and evaluates:
        - Check realisation key returns a dict
        - All datasets listed are in the datasets section
        - Check all realisations are strings
        """
        realisations = self.data.get('realisations')
        if realisations is None:
            return

        # Check if key returns a dict
        if not self._check_type('Realisations', realisations, dict):
            return

        # Check datasets are listed in the main dataset section
        realisation_datasets = set(realisations.keys())
        root_datasets = set(self.data.get('datasets',{}))

        # Check all datasets are listed in datasets section
        if not realisation_datasets.issubset(root_datasets):
            diff = realisation_datasets.difference(root_datasets)
            print(f'\t\tERROR: Unexpected dataset. Realisation datasets should match to a dataset specified in datasets section. {diff} does not match')

        # Check all realisations are strings
        for realisation in realisations:
            if not isinstance(realisation, str):
                print(f'\t\tERROR: Realisations should be strings. {realisation} is not a string')

    def test_overrides(self):
        """
        Checks the overrides section and evaluates:
        - Check overrides returns a dict
        - All the keys listed are valid
        - All the key values are lists
        """
        overrides = self.data.get('overrides')
        if overrides is None:
            return

        # Check overrides returns a dict
        if not self._check_type('Overrides', overrides, dict):
            return

        # Check all keys listed are valid
        self._check_valid_keys(overrides, self.FACET_KEYS)

    def run_test(self, callable):

        print(f'\tTEST: {callable}')
        test = getattr(self, callable)
        test()

    def run(self):

        try:
            self.test_json_formatting()
        except Exception:
            print('CRITICAL: The file cannot be read so no other tests will work')
            exit(1)

        # Load the data
        self.data = self._read_file()

        # Run the tests
        tests = [func for func in dir(self) if func.startswith('test_') and callable(getattr(self, func))]

        for test in tests:
            self.run_test(test)

    @classmethod
    def cmd(cls):
        parser = argparse.ArgumentParser(description='Check whether a given JSON file matches the expected format'
                                                     'to be used with the CCI tagger')

        parser.add_argument('json_file', help='JSON file to test', nargs='+')

        args = parser.parse_args()

        files = args.json_file

        print(f'Found {len(files)} files')

        for file in files:
            print(f'\n\nTesting {file}')

            tjf = cls(file)
            tjf.run()


if __name__ == '__main__':
    TestJSONFile.cmd()

