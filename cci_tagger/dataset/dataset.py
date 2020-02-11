# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '04 Feb 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import pathlib
import itertools
from cci_tagger.constants import DATA_TYPE, FREQUENCY, INSTITUTION, PLATFORM,\
    SENSOR, ECV, PLATFORM_PROGRAMME, PLATFORM_GROUP, PROCESSING_LEVEL,\
    PRODUCT_STRING, PRODUCT_VERSION, LEVEL_2_FREQUENCY,\
    BROADER_PROCESSING_LEVEL, ALLOWED_GLOBAL_ATTRS
from cci_tagger.file_handlers.handler_factory import HandlerFactory
import re


class Dataset(object):

    ESACCI = 'ESACCI'

    def __init__(self, dataset, dataset_json_mappings, facets, verbosity=0):
        """

        :param dataset:
        :param dataset_json_mappings:
        """

        self.dataset = dataset
        self._verbosity = verbosity
        self._facets = facets

        # JSON file loader
        self.dataset_json_mappings = dataset_json_mappings
        self.dataset_defaults = dataset_json_mappings.get_user_defined_defaults(dataset)
        self.dataset_mappings = dataset_json_mappings.get_user_defined_mapping(dataset)
        self.dataset_overrides = dataset_json_mappings.get_user_defined_overrides(dataset)

    def process_dataset(self, max_file_count=0):

        # Get a list of files in the dataset
        file_list = self.get_dataset_files(max_file_count)

        if self._verbosity >= 1:
            if max_file_count:
                print(f'Dataset: {self.dataset}\n Processing {len(file_list)} files')

        # There are no files
        if not file_list:
            print(f'WARNING: No files found for {self.dataset}')
            return

        for file in file_list:
            self.get_file_tags(file)

        return # URIs for MOLES, {} of files organised into datasets

    def get_file_tags(self, file):
        """

        :param file:
        :return:
        """
        # Get default tags
        file_tags = self.dataset_defaults

        # Get tags from filepath
        tags_from_filename = self._parse_file_name(file)
        file_tags.update(tags_from_filename)

        # Get tags from file metadata
        tags_from_metadata = self._scan_file(file, file_tags.get(PROCESSING_LEVEL))
        file_tags.update(tags_from_metadata)

        # Apply mappings
        mapped_values = self.apply_mapping(file_tags)

        # Apply any overrides
        mapped_values = self.apply_overrides(mapped_values)

        # convert tags to URIs
        uris = self.convert_terms_to_uris(mapped_values)

        return uris

    def _scan_file(self, filename, proc_level):
        """
        Scan the file and extract tags from the metadata
        :param filename:
        :return:
        """
        processed_labels = {}

        # File specific parser
        handler = HandlerFactory.get_handler(filename.suffix)

        if handler:
            labels = handler(filename).extract_facet_labels(proc_level)

            # Process file tags
            processed_labels = self._process_file_attributes(labels)

        return processed_labels

    def _process_file_attributes(self, file_attributes):

        for global_attr in ALLOWED_GLOBAL_ATTRS:
            # Get the file attribute for the given global attr
            attr = file_attributes.get(global_attr)

            # If the global attribute does not exist for this file,
            # Check defaults
            # continue
            if not attr:

                # Check user defaults for a value in this field
                if self.dataset_defaults.get(global_attr):
                    attr = self.dataset_defaults.get(global_attr)
                else:
                    continue

            # Get merged mapping fields
            attr = self.dataset_json_mappings.get_merged_attribute(self.dataset, attr)

            # Split based on separator
            if global_attr is PLATFORM:
                if '<' in attr:
                    bits = attr.split(', ')
                else:
                    bits = attr.split(',')

            else:
                bits = attr.split(',')

            # Deal with multiplatforms
            if global_attr is PLATFORM:
                bits = self.split_multiplatforms(bits)

            # Replace input attributes with output from scanning process
            file_attributes[global_attr] = bits

        return file_attributes

    def apply_mapping(self, file_tags):
        """
        Take set of file tags and map them based on user JSON files

        :param file_tags: Tags extracted from the files
        :return: Bag of mapped tags
        """
        mapped_values = {}

        for facet, values in file_tags.items():

            if type(values) is list:
                mapped_values[facet] = [self.get_mapping(facet, val) for val in values]

            elif type(values) is str:
                mapped_values[facet] = [self.get_mapping(facet, values)]

        return mapped_values

    def get_mapping(self, facet, term):
        """
        Convert the term to lower case and get the mapped value from the
        user JSON files. Will return the original term in lowercase if no
        mapping is found.

        :param facet: The facet to match against (string)
        :param term: The term to be mapped (string)
        :return: Mapped term or lowercase term (string)
        """

        # Make sure term is lowercase
        term = term.lower()

        # Check to see if there are any mappings for this facet in this dataset
        facet_map = self.dataset_mappings.get(facet)

        if facet_map:

            # Loop through the possible mappings and match the lowercase
            # term against he lowercase key in the mapping to remove
            # ambiguity.
            for key in facet_map:
                if term == key.lower():
                    return facet_map[key].lower()

        return term

    def apply_overrides(self, mapped_tags):
        """
        Apply any hard overrides which have been defined in the JSON files.
        This will take it as is, so you will need to make sure that overrides are
        legit!

        :param mapped_tags: Fields to apply overrides to
        :return: mapped_tags with overrides applies (dict)
        """

        if self.dataset_overrides:
            for facet, value in self.dataset_overrides.items():
                mapped_tags[facet] = value

        return mapped_tags

    def convert_terms_to_uris(self, mapped_labels):
        """
        Get the terms which have been extracted from the file and turn them
        into a bag or URIs which have been validated by the vocab server.

        :param mapped_labels: Mapped labels
        :return:
        """

        uri_bag = {}

        # Filename facets
        for facet in [PROCESSING_LEVEL, ECV, DATA_TYPE, PRODUCT_STRING]:
            # Get the terms
            terms = mapped_labels.get(facet)

            # Make sure input is a list
            if type(terms) is str:
                terms = [terms]

            # Retrieve set of URIs. Put them in a set to remove duplicates
            uris = set()
            for term in terms:

                # Clean any leading/trailing whitespace
                term = term.strip()

                # Get the URI for the term
                uri = self._get_term_uri(facet, term)
                if uri:
                    uris.add(uri)

                # Add broader terms for processing level
                if facet is PROCESSING_LEVEL:
                    broader_proc_level_uri = self._facets.get_broader_proc_level(uri)

                    if broader_proc_level_uri:
                        uri_bag[BROADER_PROCESSING_LEVEL] = broader_proc_level_uri

            if uris:
                uri_bag[facet] = uris

        # Metadata facets
        for facet in [FREQUENCY, INSTITUTION, PLATFORM, SENSOR]:
            terms = mapped_labels.get(facet)

            # Make sure input is a list
            if type(terms) is str:
                terms = [terms]

            uris = set()
            for term in terms:

                # Strip any trailing/leading whitespace
                term = term.strip()

                # Ignore N/A values
                if term == 'N/A':
                    continue

                # Get the URI from the vocab service
                uri = self._get_term_uri(facet, term)

                if uri:
                    uris.add(uri)

                    if facet is PLATFORM:
                        # Add the broader terms
                        uris.update(self.get_programme_group(uri))

                # If platform does not return a URI try to get platform programmes tags
                elif facet is PLATFORM:
                    platform_tags = self._get_platform_as_programme(term)
                    uris.update(platform_tags)

                    if not platform_tags:
                        # TODO: Add some kind of logging
                        pass

                else:
                    # TODO: Add some kind of logging. The term has not generated any kind of URI
                    pass

            if uris:
                uri_bag[facet] = uris

        return uri_bag

    def _get_term_uri(self, facet, term):

        facet = facet.lower()
        term_l = term.lower()

        # Check the pref labels
        if term_l in self._facets.get_labels(facet):
            return self._facets.get_labels(facet)[term_l].uri

        # Check the alt labels
        elif term_l in self._facets.get_alt_labels(facet):
            return self._facets.get_alt_labels(facet)[term_l].uri

    def convert_uris_to_drs(self):

        # Multi-label fields
        [SENSOR, PLATFORM, FREQUENCY]
        return

    def get_programme_group(self, term_uri):
        # now add the platform programme and group
        tags = []

        programme = self._facets.get_platforms_programme(term_uri)
        if programme:
            programme_uri = self._get_term_uri(PLATFORM_PROGRAMME, programme)
            tags.append(programme_uri)

            group = self._facets.get_programmes_group(programme_uri)
            if group:
                group_uri = self._get_term_uri(PLATFORM_GROUP, group)
                tags.append(group_uri)

        return tags

    def _get_platform_as_programme(self, platform):
        tags = []

        # check if the platform is really a platform programme
        if platform in self._facets.get_programme_labels():
            programme_uri = self._get_term_uri(PLATFORM_PROGRAMME, platform)
            tags.append(programme_uri)

            try:
                group = self._facets.get_programmes_group(programme_uri)
                group_uri = self._get_term_uri(PLATFORM_GROUP, group)
                tags.append(group_uri)

            except KeyError:
                # not all programmes have groups
                pass

        # check if the platform is really a platform group
        elif platform in self._facets.get_group_labels():
            group_uri = self._get_term_uri(PLATFORM_GROUP, platform)
            tags.append(group_uri)

        return tags

    @staticmethod
    def split_multiplatforms(segments):
        """
        Take a string like ERS-<1,2> and return
        ['ERS-1','ERS-2']

        :param segment: String
        :return: list of components
        """
        split_segments = []
        pattern = re.compile(r'(.*-)<(.*)>.*')

        for segment in segments:

            m = re.match(pattern, segment)
            if m:
                term = m.group(1)
                values = m.group(2).split(',')

                split_segments.extend([f'{term}{val}' for val in values])

            else:
                split_segments.append(segment)

        return split_segments

    def _parse_file_name(self,fpath):
        """
        Extract data from the file name.

        The file name comes in two different formats. The values are '-'
        delimited.
        Form 1
            <Indicative Date>[<Indicative Time>]-ESACCI
            -<Processing Level>_<CCI Project>-<Data Type>-<Product String>
            [-<Additional Segregator>][-v<GDS version>]-fv<File version>.nc
        Form 2
            ESACCI-<CCI Project>-<Processing Level>-<Data Type>-
            <Product String>[-<Additional Segregator>]-
            <IndicativeDate>[<Indicative Time>]-fv<File version>.nc

        Values extracted from the file name:
            Processing Level
            CCI Project (ecv)
            Data Type
            Product String

        @param ds (str): the full path to the dataset
        @param fpath (str): the path to the file

        @return drs and csv representations of the data

        """

        path_facet_bits = fpath.parts
        file_segments = path_facet_bits[-1].split('-')

        # TODO: Have some kind of logging procedure
        if len(file_segments) < 5:
            return {}

        if file_segments[1] == self.ESACCI:
            return self._get_data_from_filename1(file_segments)

        elif file_segments[0] == self.ESACCI:
            return self._get_data_from_filename2(file_segments)

        # TODO: Have some kind of logging procedure
        # There was an error, unable to extract any tags
        return {}
    
    @staticmethod
    def _get_data_from_filename1(file_segments):
        """
        Extract data from the file name of form 1.

        @param file_segments (List(str)): file segments

        @return a dict where:
                key = facet name
                value = file segment

        """
        return {
            PROCESSING_LEVEL: file_segments[2].split('_')[0],
            ECV: file_segments[2].split('_')[1],
            DATA_TYPE: file_segments[3],
            PRODUCT_STRING: file_segments[4]
        }

    @staticmethod
    def _get_data_from_filename2(file_segments):
        """
        Extract data from the file name of form 2.

        @param file_segments (List(str)): file segments

        @return a dict where:
                key = facet name
                value = file segment

        """
        return {
            PROCESSING_LEVEL: file_segments[2],
            ECV: file_segments[1],
            DATA_TYPE: file_segments[3],
            PRODUCT_STRING: file_segments[4]
        }

    def get_dataset_files(self, max_file_count):
        """
        Get files from the dataset. Will return a list including all file types
        unless the max_file_count parameter > 0. This assumes you are testing and
        are only interested in netCDF so will return the first n netCDF files

        :param max_file_count: Used for testing. Max number of netCDF files. Default: 0
        :return: list of files
        """

        path = pathlib.Path(self.dataset)

        if max_file_count > 0:
            # Only want a small number of netcdf files for testing
            all_netcdf = path.glob('**/*.nc')

            # Get first n
            first_n = itertools.islice(all_netcdf, max_file_count)

            return list(first_n)

        # Return all files from the dataset recursively
        return list(path.glob('**/*'))
