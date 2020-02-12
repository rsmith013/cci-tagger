'''
BSD Licence
Copyright (c) 2016, Science & Technology Facilities Council (STFC)
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
        this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
        this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.
    * Neither the name of the Science & Technology Facilities Council (STFC)
        nor the names of its contributors may be used to endorse or promote
        products derived from this software without specific prior written
        permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''

import hashlib
import json
import os

import netCDF4

from cci_tagger.constants import DATA_TYPE, FREQUENCY, INSTITUTION, PLATFORM,\
    SENSOR, ECV, PLATFORM_PROGRAMME, PLATFORM_GROUP, PROCESSING_LEVEL,\
    PRODUCT_STRING, PRODUCT_VERSION, LEVEL_2_FREQUENCY,\
    BROADER_PROCESSING_LEVEL, ALLOWED_GLOBAL_ATTRS
from cci_tagger.facets import Facets
from cci_tagger.settings import ERROR_FILE, ESGF_DRS_FILE, MOLES_TAGS_FILE,\
    MOLES_ESGF_MAPPING_FILE
from cci_tagger.triple_store import TripleStore
from cci_tagger.dataset.dataset_tree import DatasetJSONMappings
from cci_tagger.dataset.dataset import Dataset


class ProcessDatasets(object):
    """
    This class provides the process_datasets method to process datasets,
    extract data from file names and from within net cdf files. It then
    produces files for input into MOLES and ESGF.

    Some data are extracted from the file name.

    The file name comes in two different formats. The values are '-'
    delimited.
    Format 1
        <Indicative Date>[<Indicative Time>]-ESACCI
        -<Processing Level>_<CCI Project>-<Data Type>-<Product String>
        [-<Additional Segregator>][-v<GDS version>]-fv<File version>.nc
    Format 2
        ESACCI-<CCI Project>-<Processing Level>-<Data Type>-
        <Product String>[-<Additional Segregator>]-
        <IndicativeDate>[<Indicative Time>]-fv<File version>.nc

    Values extracted from the file name:
        Processing Level
        CCI Project (ecv)
        Data Type
        Product String

    Other data are extracted from the net cdf file attributes.
        time frequency
        sensor id
        platform id
        product version
        institute

    The DRS is made up of:
        project (hard coded "esacci")
        cci_project
        time frequency
        processing level
        data type
        sensor id
        platform id
        product string
        product version
        realization
        version (current date)

    Realization is used to distinguish between DRS that would otherwise be
    identical. When determining the realisation a file of mappings of dataset
    names to DRS is consulted. If the data set already exists in the list then
    the existing realisation value is reused.

    """
    ESACCI = 'ESACCI'
    DRS_ESACCI = 'esacci'

    # an instance of the facets class
    __facets = None

    __moles_facets = [BROADER_PROCESSING_LEVEL, DATA_TYPE, ECV,
                              PROCESSING_LEVEL, PRODUCT_STRING] + ALLOWED_GLOBAL_ATTRS
    __single_valued_facets = [BROADER_PROCESSING_LEVEL, DATA_TYPE, ECV,
                              PROCESSING_LEVEL, PRODUCT_STRING]
    __multi_valued_facet_labels = {
        FREQUENCY: 'multi-frequency',
        INSTITUTION: 'multi-institution',
        PLATFORM: 'multi-platform',
        SENSOR: 'multi-sensor'
    }

    def __init__(self, checksum=True, verbose=0, suppress_file_output=False,
                 json_directory=None):
        """
        Initialise the ProcessDatasets class.

        @param checksum (boolean): if True produce a checksum for each file
        @param use_mapping (boolean): if True use the local mapping to correct
                use values to match those in the vocab server
        @param verbose (int): increase output verbosity

        """
        self.__checksum = checksum
        self.__verbose = verbose
        self.__suppress_fo = suppress_file_output

        self.__facets = Facets()
        self.__file_drs = None
        self.__file_csv = None
        self._open_files()
        self.__not_found_messages = set()
        self.__error_messages = set()
        self.__ds_drs_mapping = set()
        self.__dataset_json_values = DatasetJSONMappings(json_directory)

    def _check_property_value(self, value, labels, facet, defaults_source):
        if value not in labels:
            print ('ERROR "{value}" in {file} is not a valid value for '
                   '{facet}. Should be one of {labels}.'.
                   format(value=value, file=defaults_source,
                          facet=facet, labels=', '.join(sorted(labels))))
            exit(1)
        return True

    def process_datasets(self, datasets, max_file_count=0):
        """
        Loop through the datasets pulling out data from file names and from
        within net cdf files.

        @param datasets (List(str)): a list of dataset names, these are the
        full paths to the datasets
        @param max_file_count (int): how many .nc files to look at per dataset.
                If the value is less than 1 then all datasets will be
                processed.

        """
        ds_len = len(datasets)
        if self.__verbose >= 1:
            if max_file_count > 0:
                print("Processing a maximum of %s files for each of %s "
                      "datasets" % (max_file_count, ds_len))
            else:
                print("Processing %s datasets" % ds_len)

        # A sanity check to let you see what files are being included in each dataset
        dataset_file_mapping = {}

        for dspath in sorted(datasets):
            dataset_id = self.__dataset_json_values.get_dataset(dspath)
            dataset = Dataset(dataset_id, self.__dataset_json_values, self.__facets, self.__verbose)

            dataset_uris, ds_file_map = dataset.process_dataset(max_file_count)

            self._write_moles_tags(dataset_id, dataset_uris)

            dataset_file_mapping.update(ds_file_map)

        self._write_json(dataset_file_mapping)

        if len(self.__not_found_messages) > 0:
            # TODO: Output a list of terms not in the vocab
            print("\nSUMMARY OF TERMS NOT IN THE VOCAB:\n")
            for message in sorted(self.__not_found_messages):
                print(message)

        with open(ERROR_FILE, 'w') as f:
            # TODO: Some kind of error framework
            for message in sorted(self.__error_messages):
                f.write('%s\n' % message)

        self._close_files()

    def get_file_tags(self, fpath):
        """
        Extracts the facet labels from the tags
        USED BY THE FACET SCANNER FOR THE CCI PROJECT
        :param fpath: Path the file to scan
        :return: drs identifier (string), facet labels (dict)
        """
        # TODO: SORT OUT HOW THE FACET SCANNER WORKS AND USES THIS INFORMATION

        # Get the dataset
        ds = self.__dataset_json_values.get_dataset(fpath)

        dataset = Dataset(ds, self.__dataset_json_values, self.__facets, self.__verbose)
        uris = dataset.get_file_tags(fpath)

        # Turn uris into human readable tags
        tags = self.__facets.process_bag(uris)

        # Get DRS labels
        drs_facets = dataset.get_drs_labels(tags)

        # Generate DRS id
        drs = self._generate_ds_id(ds, drs_facets)

        return drs, tags


    def _process_dataset(self, ds, count, drs, max_file_count):
        """
        Pull out data from file names and from within net cdf files.

        @param ds (str): the full path to the dataset
        @param count (int): the sequence number for this dataset
        @param drs {dict}: key (str) = DRS label
                           value (dict):
                               key = 'file', value = the file path
                               key = 'sha256', value = the sha256 of the file
                               key = 'size', value = the siz of the file
                               key = 'mtime', value = the mtime of the file
        @param max_file_count (int): how many .nt files to look at per dataset
                If the value is less than 1 then all datasets will be
                processed.

        """
        tags_ds = dict(self.__user_assigned_defaults_uris)
        drs_count = 0

        # key drs id, value realization
        current_drs_ids = {}

        # get a list of files
        nc_files = self._get_nc_files(ds, max_file_count)

        if self.__verbose >= 1:
            print("\nDataset %s Processing %s files from %s" %
                  (count, len(nc_files), ds))

        if len(nc_files) == 0:
            self.__error_messages.add('WARNING %s, no .nc files found' % (ds))
            return

        for fpath in nc_files:

            drs_facets = {}

            net_cdf_drs, net_cdf_tags = self._get_tags(ds, fpath)

            # Update the user defined defaults
            drs_facets.update(net_cdf_drs)
            tags_ds.update(net_cdf_tags)

            dataset_id = self._generate_ds_id(ds, drs_facets)

            # only add files with all of the drs data
            if dataset_id is None or drs_facets.get('error'):
                continue

            if self.__checksum:
                sha256 = self._sha256(fpath)
                mtime = os.path.getmtime(fpath)
                size = os.path.getsize(fpath)

                if dataset_id in drs.keys():
                    drs[dataset_id].append({
                        'file': fpath,
                        'sha256': sha256,
                        'mtime': mtime,
                        'size': size
                    })

                else:
                    drs_count = drs_count + 1
                    drs[dataset_id] = [{
                        'file': fpath,
                        'sha256': sha256,
                        'mtime': mtime,
                        'size': size
                    }]

            else:
                if dataset_id in drs.keys():
                    drs[dataset_id].append({'file': fpath})

                else:
                    drs_count = drs_count + 1
                    drs[dataset_id] = [{'file': fpath}]

                    if self.__verbose >= 1:
                        print(f'DRS = {dataset_id}')

        if drs_count == 0:
            self.__error_messages.add(
                f'ERROR in {ds}, no DRS entries created')

        if self.__verbose >= 1:
            print(f"Created {drs_count} DRS {'entry' if drs_count == 1 else 'entries'}")

        self._write_moles_tags(ds, tags_ds)

    def _sha256(self, fpath):
        """
        Generate the sha256 for the given file.

        @param (str): the path to the file

        @return the sha256 of the file

        """
        if self.__verbose >= 2:
            print('Generating sha256')
        h = hashlib.sha256()
        f = open(fpath)
        while True:
            data = f.read(10240)
            if not data:
                break
            h.update(data)
        f.close()
        return h.hexdigest()

    def _get_nc_files(self, dir_, max_file_count):
        """
        Get the list of net cdf files in the given directory.

        @param dir_ (str): the name of the directory to scan
        @param max_file_count (int): how many .nt files to look at per dataset
                If the value is less than 1 then all datasets will be
                processed.

        @return a list of file names complete with paths

        """
        if all([os.path.isfile(x) for x in dir_]):
            return dir_
        
        file_list = []
        count = 1
        for root, _, files in os.walk(dir_):
            for name in files:
                if name.endswith('.nc'):
                    file_list.append(os.path.join(root, name))
                    count = count + 1
                    if max_file_count > 0 and count > max_file_count:
                        return file_list
        return file_list

    def _parse_file_name(self, ds, fpath):
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

        path_facet_bits = fpath.split('/')
        last_bit = len(path_facet_bits) - 1
        file_segments = path_facet_bits[last_bit].split('-')

        if len(file_segments) < 5:
            message_found = False

            # Do not add another message if we have already reported an invalid
            # file name for this dataset
            for message in self.__error_messages:
                if message.startswith(f'ERROR in {ds}, invalid file name format'):
                    message_found = True

            if not message_found:
                self.__error_messages.add(
                    f'ERROR in {ds}, invalid file name format "{path_facet_bits[last_bit]}"'
                )

            return {}, {}

        if file_segments[1] == self.ESACCI:
            return self._process_form(
                ds, self._get_data_from_file_name_1(file_segments)
            )

        elif file_segments[0] == self.ESACCI:
            return self._process_form(
                ds, self._get_data_from_file_name_2(file_segments)
            )

        else:
            message_found = False

            # Do not add another message if we have already reported an invalid
            # file name for this dataset
            for message in self.__error_messages:
                if message.startswith(f'ERROR in {ds}, invalid file name format'):
                    message_found = True

            if not message_found:
                self.__error_messages.add(
                    f'ERROR in {ds}, invalid file name format "{path_facet_bits[last_bit]}"'
                )

            return {}, {}

    @staticmethod
    def _get_data_from_file_name_1(file_segments):
        """
        Extract data from the file name of form 1.

        @param file_segments (List(str)): file segments

        @return a dict where:
                key = facet name
                value = file segment

        """
        form = {}
        form[PROCESSING_LEVEL] = file_segments[2].split('_')[0]
        form[ECV] = file_segments[2].split('_')[1]
        form[DATA_TYPE] = file_segments[3]
        form[PRODUCT_STRING] = file_segments[4]

        return form

    @staticmethod
    def _get_data_from_file_name_2(file_segments):
        """
        Extract data from the file name of form 2.

        @param file_segments (List(str)): file segments

        @return a dict where:
                key = facet name
                value = file segment

        """
        form = {}
        form[PROCESSING_LEVEL] = file_segments[2]
        form[ECV] = file_segments[1]
        form[DATA_TYPE] = file_segments[3]
        form[PRODUCT_STRING] = file_segments[4]

        return form

    def _process_form(self, ds, form):
        """
        Process form to generate drs and csv representations.

        @param ds (str): the full path to the dataset
        @param form (dict): data extracted from the file name

        @return drs and csv representations of the data

        """
        csv_rec = {}

        facets = [PROCESSING_LEVEL, ECV, DATA_TYPE, PRODUCT_STRING]

        for facet in facets:
            term = self._get_term_uri(facet, form[facet])

            if term:
                csv_rec[facet] = term

                if facet == PROCESSING_LEVEL:
                    # add broader terms for the processing level
                    broader_proc_level = self.__facets.get_broader_proc_level(term)

                    if broader_proc_level is not None:
                        csv_rec[BROADER_PROCESSING_LEVEL] = broader_proc_level

            else:
                # No term, add error messages
                self.__not_found_messages.add(f'{facet}: {form[facet]}')
                self.__error_messages.add(f'ERROR in {ds} for {facet}, invalid value "{form[facet]}"')

        return self._create_drs_record(csv_rec), csv_rec

    def _create_drs_record(self, csv_rec):

        drs = {}

        for facet in [PROCESSING_LEVEL, ECV, DATA_TYPE, PRODUCT_STRING]:
            label = self.__facets.get_label_from_uri(facet, csv_rec.get(facet))

            if label:
                drs[facet] = label

        return drs

    def _scan_net_scan_net_cdf_file_cdf_file(self, fpath, ds, processing_level):
        """
        Extract data from the net cdf file.

        The values to extract are take from the know_attr list which are the
        keys of the attr_mapping dictionary.

        """
        drs = {}
        tags = {}

        try:
            nc = netCDF4.Dataset(fpath)

        except Exception:
            self.__error_messages.add(
                f'ERROR in {ds}, extracting attributes from "{fpath}"')

            return drs, tags

        if self.__verbose >= 2:
            print(f'GLOBAL ATTRS for {fpath}: ')

        for global_attr in nc.ncattrs():
            if self.__verbose >= 2:
                print(global_attr, "=", nc.getncattr(global_attr))

            if (global_attr.lower() == FREQUENCY and
                    processing_level is not None and '2' in processing_level):

                # do something special for level 2 data
                drs[FREQUENCY] = (
                    TripleStore.get_pref_label(LEVEL_2_FREQUENCY))
                tags[FREQUENCY] = [LEVEL_2_FREQUENCY]

            elif global_attr.lower() in ALLOWED_GLOBAL_ATTRS:
                attr = nc.getncattr(global_attr)

                a_drs, a_tags = self._process_file_atrib(
                    global_attr.lower(), attr, ds)

                # Update tags
                drs.update(a_drs)
                tags.update(a_tags)

            # we don't have a vocab for product_version
            elif global_attr.lower() == PRODUCT_VERSION:
                attr = self._convert_term(
                    PRODUCT_VERSION, nc.getncattr(global_attr))

                drs[PRODUCT_VERSION] = attr
                tags[PRODUCT_VERSION] = attr

        if self.__verbose >= 3:
            print('VARIABLES...')

        for (var_id, var) in nc.variables.items():
            if self.__verbose >= 3:
                print(f'\tVARIABLE ATTRIBUTES ({var_id})')

            if var_id == 'time':
                if var.dimensions == ():
                    self.__error_messages.add(
                        f'ERROR in {ds}, time has no dimensions')
                    drs['error'] = True

            for attr in var.ncattrs():
                if self.__verbose >= 3:
                    print(f'\t\t{attr}={var.getncattr(attr)}')

                if (attr.lower() == 'long_name' and len(var.getncattr(attr)) == 0):
                    self.__error_messages.add(
                        f'WARNING in {ds}, long_name value has zero length')

        return drs, tags

    def _process_file_atrib(self, global_attr, attr, ds):
        """
        Process tag extracted from the file
        :param global_attr: Facet (e.g. PLATFORM, SENSOR,...)
        :param attr: The extracted tag from the file
        :param ds: Dataset in current processing. Used for logging.
        :return: (drs labels, uri tags)
        """

        # Set up empty dictionaries to hold results
        drs = {}
        tags = {}

        # Split based on separator
        if global_attr == PLATFORM:
            if '<' in attr:
                bits = attr.split(', ')
            else:
                bits = attr.split(',')

        elif global_attr in [INSTITUTION, SENSOR, FREQUENCY]:
            bits = attr.split(',')

        else:
            bits = [attr]

        # Hack to deal with multi platforms
        # TODO do in generic way
        if global_attr == PLATFORM:
            if 'NOAA-<12,14,15,16,17,18>' in bits:
                bits.remove('NOAA-<12,14,15,16,17,18>')
                bits.extend(
                    ['NOAA-12', 'NOAA-14', 'NOAA-15', 'NOAA-16', 'NOAA-17',
                     'NOAA-18'])
            if 'ERS-<1,2>' in bits:
                bits.remove('ERS-<1,2>')
                bits.extend(['ERS-1', 'ERS-2'])

        term_count = 0
        for bit in bits:
            bit = bit.strip()

            if bit == 'N/A':
                continue

            term_uri = self._get_term_uri(global_attr, bit)

            if term_uri:

                # Add term to the drs
                drs[global_attr] = (self.__facets.get_label_from_uri(global_attr, term_uri))

                # Create a set to filter out duplicate uris
                if term_count == 0:
                    tags[global_attr] = set()

                tags[global_attr].add(term_uri)
                term_count = term_count + 1

                if global_attr == PLATFORM and bit != "N/A":
                    # add the broader terms
                    for tag in self._get_programme_group(term_uri):
                        tags[global_attr].add(tag)

            elif global_attr == PLATFORM:

                p_tags = self._get_platform_as_programme(bit)

                if not p_tags:
                    self._attrib_not_found_message(ds, global_attr, attr, bit)

                elif term_count == 0:
                    # p_tags evaluates to true which means it is not an empty list
                    tags[PLATFORM] = set()

                    # we are adding a programme or group to the list of
                    # platforms, hence adding more than one platform to the
                    # count to ensure encoded as multi platform
                    term_count = term_count + 2

                # Add all the tags to the set
                if p_tags:
                    tags[PLATFORM].update(p_tags)

            else:
                self._attrib_not_found_message(ds, global_attr, attr, bit)

        if term_count > 1 and (global_attr in [SENSOR, PLATFORM, FREQUENCY]):
            drs[global_attr] = self.__multi_valued_facet_labels[global_attr]


        if not drs:
            if global_attr not in [PLATFORM, SENSOR]:
                if attr != 'N/A':
                    self.__error_messages.add(f'ERROR in {ds} for {global_attr}, invalid value "{attr}"')

        return drs, tags

    def _attrib_not_found_message(self, ds, global_attr, attr, value):

        self.__not_found_messages.add("%s: %s" % (global_attr, value))

        if value == attr:
            self.__error_messages.add('ERROR in %s for %s, invalid value "%s"'
                                      % (ds, global_attr, value))

        else:
            self.__error_messages.add('ERROR in %s for %s, invalid value "%s" '
                                      'in "%s"' % (ds, global_attr, value,
                                                   attr))



    def _generate_ds_id(self, ds, drs_facets):

        error = False
        facets = [ECV, FREQUENCY, PROCESSING_LEVEL, DATA_TYPE, SENSOR,
                  PLATFORM, PRODUCT_STRING, PRODUCT_VERSION]

        ds_id = self.DRS_ESACCI

        for facet in facets:

            facet_value = drs_facets.get(facet)

            if not facet_value:
                # facet_value is either None or empty and is an error
                error = True
                message_found = False

                # Do not add another message if we have already reported an
                # invalid value
                for message in self.__error_messages:
                    if message.startswith(
                            f'ERROR in {ds} for {facet}, invalid value'):
                        message_found = True
                        break

                if not message_found:
                    self.__error_messages.add(
                        f'ERROR in {ds} for {facet}, value not found'
                    )

            else:
                facet_value = str(drs_facets[facet]).replace('.', '-')
                facet_value = facet_value.replace(' ', '-')

                if facet == FREQUENCY:
                    facet_value = facet_value.replace('month', 'mon')
                    facet_value = facet_value.replace('year', 'yr')

                ds_id = f'{ds_id}.{facet_value}'

        if error:
            return

        # Add realisation
        ds_id = f'{ds_id}.{self._get_realisation(ds)}'

        return ds_id

    def _get_realisation(self, ds):
        """
        Get the realisation value for the dataset. This will default
        to r1 but can be changed by modifying/creating a dataset
        JSON file

        :param ds: Path to dataset (String)
        :return: realisation (String)
        """

        return 'r1'

    def _write_moles_tags(self, ds, uris):
        """

        :param ds: Dataset (will be a file path)
        :param uris: Dictionary of extracted tags as URIS to the vocab service
        """

        for facet in self.__moles_facets:
            tags = uris.get(facet)
            if tags:
                self._write_moles_tags_out(ds, tags)

    def _write_moles_tags_out(self, ds, uri):

        if self.__suppress_fo:
            return

        else:
            self.__file_csv.write(f'{ds},{uri}\n')

    def _write_json(self, drs):
        if self.__suppress_fo:
            return

        self.__file_drs.write(
            json.dumps(drs, sort_keys=True, indent=4, separators=(',', ': ')))


    def _open_files(self, ):
        # Do not open files if suppress output is true
        if self.__suppress_fo:
            return

        self.__file_csv = open(MOLES_TAGS_FILE, 'w')

        self.__file_drs = open(ESGF_DRS_FILE, 'w')

    def _close_files(self, ):
        if self.__suppress_fo:
            return

        self.__file_csv.close()

        self.__file_drs.close()
