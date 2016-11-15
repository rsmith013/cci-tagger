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
from time import strftime

import netCDF4

from cci_tagger.constants import DATA_TYPE, FREQUENCY, INSTITUTION, PLATFORM,\
    SENSOR, ECV, PLATFORM_PROGRAMME, PLATFORM_GROUP, PROCESSING_LEVEL,\
    PRODUCT_STRING, PRODUCT_VERSION, LEVEL_2_FREQUENCY,\
    BROADER_PROCESSING_LEVEL
from cci_tagger.facets import Facets
from cci_tagger.mappings import LocalVocabMappings
from cci_tagger.properties_parser import Properties
from cci_tagger.settings import ERROR_FILE, ESGF_DRS_FILE, MOLES_TAGS_FILE,\
    MOLES_ESGF_MAPPING_FILE
from cci_tagger.triple_store import TripleStore


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
    MULTI_SENSOR = 'multi-sensor'
    MULTI_PLATFORM = 'multi-platform'
    MULTI_FREQUENCY = 'multi-frequency'

    # an instance of the facets class
    __facets = None

    __allowed_net_cdf_attribs = [FREQUENCY, INSTITUTION, PLATFORM, SENSOR]

    def __init__(self, checksum=True, use_mapping=True, verbose=0,
                 update_moles=False, default_terms_file=None):
        """
        Initialise the ProcessDatasets class.

        @param checksum (boolean): if True produce a checksum for each file
        @param use_mapping (boolean): if True use the local mapping to correct
                use values to match those in the vocab server
        @param verbose (int): increase output verbosity

        """
        self.__checksum = checksum
        self.__use_mapping = use_mapping
        self.__verbose = verbose
        self.__update_moles = update_moles
        if self.__update_moles:
            try:
                from tools.vocab_tools.tag_obs_with_vocab_terms import \
                    tag_observation
                self._tag_observation = tag_observation
            except ImportError:
                print('Oops. Looks like you have selected to write to MOLES '
                      'but we cannot find the MOLES library')
                exit(1)
        if self.__facets is None:
            self.__facets = Facets()
        self.__file_drs = None
        self.__file_csv = None
        self._open_files()
        self.__not_found_messages = set()
        self.__error_messages = set()
        self.__ds_drs_mapping = set()
        self.__drs_version = 'v{}'.format(strftime("%Y%m%d"))
        self.__user_assigned_defaults = self._init_user_assigned_defaults(
            default_terms_file)

    def _init_user_assigned_defaults(self, default_terms_file):
        if default_terms_file is None:
            return {}

        properties = Properties(default_terms_file).properties()
        # validate the user values against data from the triple store
        for key in properties.keys():
            try:
                labels = self.__facets.get_labels((key.lower())).keys()
            except KeyError:
                print('ERROR "{key}" in {file} is not a valid facet value. '
                      'Should be one of {facets}.'.
                      format(key=key, file=default_terms_file,
                             facets=', '.join(sorted(properties.keys()))))
                exit(1)
            if properties[key].lower() not in labels:
                print ('ERROR "{value}" in {file} is not a valid value for '
                       '{facet}. Should be one of {labels}.'.
                       format(value=properties[key], file=default_terms_file,
                              facet=key, labels=', '.join(sorted(labels))))
                exit(1)
        return properties

    def process_datasets(self, datasets, max_file_count):
        """
        Loop through the datasets pulling out data from file names and from
        within net cdf files.

        @param datasets (List(str)): a list of dataset names, these are the
        full paths to the datasets
        @param max_file_count (int): how many .nt files to look at per dataset.
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
        drs = {}
        count = 0

        for ds in sorted(datasets):
            count = count + 1
            self._process_dataset(ds, count, drs, max_file_count)

        self._write_json(drs)

        if len(self.__not_found_messages) > 0:
            print("\nSUMMARY OF TERMS NOT IN THE VOCAB:\n")
            for message in sorted(self.__not_found_messages):
                print(message)

        with open(ERROR_FILE, 'w') as f:
            for message in sorted(self.__error_messages):
                f.write('%s\n' % message)

        self._write_moles_drs_mapping()

        self._close_files()

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
        tags_ds = dict(self.__user_assigned_defaults)
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
            # the terms to be used to generate the DRS
            drs_facets = dict(self.__user_assigned_defaults)

            net_cdf_drs, net_cdf_tags = self._parse_file_name(
                ds, fpath)
            drs_facets.update(net_cdf_drs)
            tags_ds.update(net_cdf_tags)
            net_cdf_drs, net_cdf_tags = self._scan_net_cdf_file(
                fpath, ds, net_cdf_tags.get(PROCESSING_LEVEL))
            drs_facets.update(net_cdf_drs)
            tags_ds.update(net_cdf_tags)

            dataset_id = self._generate_ds_id(ds, drs_facets)
            # only add files with all of the drs data
            if dataset_id is None or drs_facets.get('error'):
                continue

            if dataset_id not in current_drs_ids.keys():
                current_drs_ids[dataset_id] = self._get_next_realization(
                    ds, dataset_id, drs)
                dataset_id = '%s.%s' % (dataset_id,
                                        current_drs_ids[dataset_id])
                self.__ds_drs_mapping.add((ds, dataset_id, self.__drs_version))
                dataset_id = '%s.%s' % (dataset_id, self.__drs_version)
            else:
                dataset_id = '%s.%s.%s' % (
                    dataset_id, current_drs_ids[dataset_id],
                    self.__drs_version)

            if self.__checksum:
                sha256 = self._sha256(fpath)
                mtime = os.path.getmtime(fpath)
                size = os.path.getsize(fpath)
                if dataset_id in drs.keys():
                    drs[dataset_id].append({'file': fpath, 'sha256': sha256,
                                            'mtime': mtime, 'size': size})
                else:
                    drs_count = drs_count + 1
                    drs[dataset_id] = [{'file': fpath, 'sha256': sha256,
                                        'mtime': mtime, 'size': size}]
            else:
                if dataset_id in drs.keys():
                    drs[dataset_id].append({'file': fpath})
                else:
                    drs_count = drs_count + 1
                    drs[dataset_id] = [{'file': fpath}]
                    if self.__verbose >= 1:
                        print('DRS = %s' % dataset_id)

        if drs_count == 0:
            self.__error_messages.add(
                'ERROR in %s, no DRS entries created' % (ds))

        if self.__verbose >= 1:
            print("Created {count} DRS {entry}".format(
                count=drs_count, entry='entry'
                if drs_count == 1 else 'entries'))

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
                if (message.startswith('ERROR in %s, invalid file name format'
                                       % (ds))):
                    message_found = True
            if not message_found:
                self.__error_messages.add(
                    'ERROR in %s, invalid file name format "%s"' %
                    (ds, path_facet_bits[last_bit]))
            return {}, {}

        if file_segments[1] == self.ESACCI:
            return self._process_form(
                ds, self._get_data_from_file_name_1(file_segments))
        elif file_segments[0] == self.ESACCI:
            return self._process_form(
                ds, self._get_data_from_file_name_2(file_segments))
        else:
            message_found = False
            # Do not add another message if we have already reported an invalid
            # file name for this dataset
            for message in self.__error_messages:
                if (message.startswith('ERROR in %s, invalid file name format'
                                       % (ds))):
                    message_found = True
            if not message_found:
                self.__error_messages.add(
                    'ERROR in %s, invalid file name format "%s"' %
                    (ds, path_facet_bits[last_bit]))
            return {}, {}

    def _get_data_from_file_name_1(self, file_segments):
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

    def _get_data_from_file_name_2(self, file_segments):
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
        term = self._get_term_uri(
            PROCESSING_LEVEL, form[PROCESSING_LEVEL], ds)
        if term is not None:
            csv_rec[PROCESSING_LEVEL] = term
            # add broader terms for the processing level
            broader_proc_level = self.__facets.get_broader_proc_level(term)
            if broader_proc_level is not None:
                csv_rec[BROADER_PROCESSING_LEVEL] = broader_proc_level
        else:
            self.__not_found_messages.add("%s: %s" %
                                          (PROCESSING_LEVEL,
                                           form[PROCESSING_LEVEL]))
            self.__error_messages.add(
                'ERROR in %s for %s, invalid value "%s"' %
                (ds, PROCESSING_LEVEL, form[PROCESSING_LEVEL]))

        term = self._get_term_uri(
            ECV, form[ECV], ds)
        if term is not None:
            csv_rec[ECV] = term
        else:
            self.__not_found_messages.add("%s: %s" % (ECV, form[ECV]))
            self.__error_messages.add(
                'ERROR in %s for %s, invalid value "%s"' %
                (ds, ECV, form[ECV]))

        term = self._get_term_uri(
            DATA_TYPE, form[DATA_TYPE], ds)
        if term is not None:
            csv_rec[DATA_TYPE] = term
        else:
            self.__not_found_messages.add("%s: %s" % (DATA_TYPE,
                                                      form[DATA_TYPE]))
            self.__error_messages.add(
                'ERROR in %s for %s, invalid value "%s"' %
                (ds, DATA_TYPE, form[DATA_TYPE]))

        term = self._get_term_uri(
            PRODUCT_STRING, form[PRODUCT_STRING], ds)
        if term is not None:
            csv_rec[PRODUCT_STRING] = term
        else:
            self.__not_found_messages.add("%s: %s" % (PRODUCT_STRING,
                                                      form[PRODUCT_STRING]))
            self.__error_messages.add(
                'ERROR in %s for %s, invalid value "%s"' %
                (ds, PRODUCT_STRING, form[PRODUCT_STRING]))

        return self._create_drs_record(csv_rec), csv_rec

    def _create_drs_record(self, csv_rec):
        proc_lev_label = TripleStore.get_alt_label(
            csv_rec.get(PROCESSING_LEVEL))
        project_label = TripleStore.get_alt_label(csv_rec.get(ECV))
        data_type_label = TripleStore.get_alt_label(csv_rec.get(DATA_TYPE))
        product_label = TripleStore.get_pref_label(csv_rec.get(PRODUCT_STRING))
        drs = {}
        if project_label != '':
            drs[ECV] = project_label
        if proc_lev_label != '':
            drs[PROCESSING_LEVEL] = proc_lev_label
        if data_type_label != '':
            drs[DATA_TYPE] = data_type_label
        if product_label != '':
            drs[PRODUCT_STRING] = product_label
        return drs

    def _scan_net_cdf_file(self, fpath, ds, processing_level):
        """
        Extract data from the net cdf file.

        The values to extract are take from the know_attr list which are the
        keys of the attr_mapping dictionary.

        """
        drs = {}
        tags = {}
        try:
            nc = netCDF4.Dataset(fpath)
        except:
            self.__error_messages.add(
                'ERROR in %s, extracting attributes from "%s"' % (ds, fpath))
            return drs, tags

        if self.__verbose >= 2:
            print("GLOBAL ATTRS for %s: " % fpath)
        for global_attr in nc.ncattrs():
            if self.__verbose >= 2:
                print(global_attr, "=", nc.getncattr(global_attr))

            if (global_attr.lower() == FREQUENCY and
                    processing_level is not None and '2' in processing_level):
                # do something special for level 2 data
                drs[FREQUENCY] = (
                    TripleStore.get_pref_label(LEVEL_2_FREQUENCY))
                tags[FREQUENCY] = [LEVEL_2_FREQUENCY]
            elif global_attr.lower() in self.__allowed_net_cdf_attribs:
                attr = nc.getncattr(global_attr)
                a_drs, a_tags = self._process_file_atrib(
                    global_attr.lower(), attr, ds)
                drs.update(a_drs)
                tags.update(a_tags)
            # we don't have a vocab for product_version
            elif global_attr.lower() == PRODUCT_VERSION:
                attr = nc.getncattr(global_attr)
                drs[PRODUCT_VERSION] = attr
                tags[PRODUCT_VERSION] = attr

        if self.__verbose >= 3:
            print("VARIABLES...")
        for (var_id, var) in nc.variables.items():
            if self.__verbose >= 3:
                print("\tVARIABLE ATTRIBUTES (%s)" % var_id)
            if var_id == 'time':
                if var.dimensions == ():
                    self.__error_messages.add(
                        'ERROR in %s, time has no dimensions' % ds)
                    drs['error'] = True
            for attr in var.ncattrs():
                if self.__verbose >= 3:
                    print("\t\t%s=%s" % (attr, var.getncattr(attr)))
                if (attr.lower() == 'long_name' and
                        len(var.getncattr(attr)) == 0):
                    self.__error_messages.add(
                        'WARNING in %s, long_name value has zero length' % ds)

        return drs, tags

    def _process_file_atrib(self, global_attr, attr, ds):
        drs = {}
        tags = {}
        if self.__use_mapping:
            attr = LocalVocabMappings.split_attrib(attr)

        if global_attr == PLATFORM:
            if '<' in attr:
                bits = attr.split(', ')
            else:
                bits = attr.split(',')
        elif (global_attr == INSTITUTION or global_attr == SENSOR or
              global_attr == FREQUENCY):
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
            term_uri = self._get_term_uri(global_attr, bit.strip())
            if term_uri is not None:
                # A term found in the vocab
                drs[global_attr] = (TripleStore.get_pref_label(term_uri))
                if term_count == 0:
                    tags[global_attr] = set()
                tags[global_attr].add(term_uri)
                term_count = term_count + 1

                if global_attr == PLATFORM and bit.strip() != "N/A":
                    # add the broader terms
                    for tag in self._get_programme_group(term_uri):
                        tags[global_attr].add(tag)

            elif global_attr == PLATFORM:
                # This is an unknown platform
                if bit.strip() == "N/A":
                    continue
                p_tags = self._get_paltform_as_programme(bit.strip())
                if len(p_tags) > 0 and term_count == 0:
                    tags[PLATFORM] = set()
                    # we are adding a programme or group to the list of
                    # platforms, hence adding more than one platform to the
                    # count to ensure encoded as multi platform
                    term_count = term_count + 2
                if len(p_tags) == 0:
                    self._attrib_not_found_message(ds, global_attr, attr,
                                                   bit.strip())

                for tag in p_tags:
                    tags[PLATFORM].add(tag)

            elif global_attr == SENSOR and bit.strip() == "N/A":
                pass

            else:
                self._attrib_not_found_message(ds, global_attr, attr,
                                               bit.strip())

        if term_count > 1 and global_attr == SENSOR:
            drs[global_attr] = self.MULTI_SENSOR
        elif term_count > 1 and global_attr == PLATFORM:
            drs[global_attr] = self.MULTI_PLATFORM
        elif term_count > 1 and global_attr == FREQUENCY:
            drs[global_attr] = self.MULTI_FREQUENCY

        if (drs == {} and not((global_attr == PLATFORM or
                               global_attr == SENSOR) and (attr == "N/A"))):
            self.__error_messages.add('ERROR in %s for %s, invalid value "%s"'
                                      % (ds, global_attr, attr))

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

    def _get_programme_group(self, term_uri):
        # now add the platform programme and group
        tags = []
        programme = self.__facets.get_platforms_programme(term_uri)
        programme_uri = self._get_term_uri(
            PLATFORM_PROGRAMME, programme)
        tags.append(programme_uri)
        try:
            group = self.__facets.get_programmes_group(programme_uri)
            group_uri = self._get_term_uri(PLATFORM_GROUP, group)
            tags.append(group_uri)
        except KeyError:
            # not all programmes have groups
            pass
        return tags

    def _get_paltform_as_programme(self, platform):
        tags = []
        # check if the platform is really a platform programme
        if (platform in self.__facets.get_programme_labels()):
            programme_uri = self._get_term_uri(PLATFORM_PROGRAMME, platform)
            tags.append(programme_uri)
            try:
                group = self.__facets.get_programmes_group(programme_uri)
                group_uri = self._get_term_uri(PLATFORM_GROUP, group)
                tags.append(group_uri)
            except KeyError:
                # not all programmes have groups
                pass

        # check if the platform is really a platform group
        elif (platform in self.__facets.get_group_labels()):
            group_uri = self._get_term_uri(PLATFORM_GROUP, platform)
            tags.append(group_uri)

        return tags

    def _generate_ds_id(self, ds, drs_facets):
        error = False
        facets = [ECV, FREQUENCY, PROCESSING_LEVEL, DATA_TYPE, SENSOR,
                  PLATFORM, PRODUCT_STRING, PRODUCT_VERSION]
        ds_id = self.DRS_ESACCI
        for facet in facets:
            try:
                if drs_facets[facet] == '':
                    error = True
                    message_found = False
                    # Do not add another message if we have already reported an
                    # invalid value
                    for message in self.__error_messages:
                        if (message.startswith(
                                'ERROR in %s for %s, invalid value' %
                                (ds, facet))):
                            message_found = True
                    if not message_found:
                        self.__error_messages.add(
                            'ERROR in %s for %s, value not found' %
                            (ds, facet))

                else:
                    facet_value = str(drs_facets[facet]).replace(
                        '.', '-').replace(' ', '-')
                    if facet == FREQUENCY:
                        facet_value = facet_value.replace(
                            'month', 'mon').replace('year', 'yr')
                    ds_id = '%s.%s' % (ds_id, facet_value)
            except(KeyError):
                error = True
                message_found = False
                # Do not add another message if we have already reported an
                # invalid value
                for message in self.__error_messages:
                    if (message.startswith('ERROR in %s for %s, invalid value'
                                           % (ds, facet))):
                        message_found = True
                if not message_found:
                    self.__error_messages.add(
                        'ERROR in %s for %s, value not found' % (ds, facet))
        if error:
            return None

        return ds_id

    def _get_next_realization(self, ds, drs_id, drs):
        realization_no = 1
        while True:
            ds_id_r = '%s.r%s.%s' % (drs_id, realization_no,
                                     self.__drs_version)
            if ds_id_r not in drs.keys():
                return 'r%s' % (realization_no)
            realization_no = realization_no + 1

    def _write_moles_tags(self, ds, drs):
        single_values = [BROADER_PROCESSING_LEVEL, DATA_TYPE, ECV,
                         PROCESSING_LEVEL, PRODUCT_STRING]
        multi_values = [FREQUENCY, INSTITUTION, PLATFORM, SENSOR]
        if self.__update_moles:
            if self.__verbose >= 2:
                print('Updating MOLES tags')
        for value in single_values:
            try:
                self._write_moles_tags_out(ds, drs[value])
            except KeyError:
                pass

        for value in multi_values:
            try:
                for uri in drs[value]:
                    self._write_moles_tags_out(ds, uri)
            except KeyError:
                pass

    def _write_moles_tags_out(self, ds, uri):
        if self.__update_moles:
            self._tag_observation(ds, uri, 'clipc_skos_vocab')
        else:
            self.__file_csv.write('{ds},{uri}\n'.format(ds=ds, uri=uri))

    def _write_moles_drs_mapping(self):
        if self.__update_moles:
            self._write_moles_drs_mapping_to_moles()
        else:
            self._write_moles_drs_mapping_to_file()

    def _write_moles_drs_mapping_to_moles(self):
        if self.__verbose >= 2:
            print('Updating MOLES ESGF mapping')
        from tools.esgf_tools.add_drs_datasets import add_mapping
        for directory, drs_id, version in self.__ds_drs_mapping:
            add_mapping(directory, drs_id, version)

    def _write_moles_drs_mapping_to_file(self):
        with open(MOLES_ESGF_MAPPING_FILE, 'w') as f:
            for directory, drs_id, version in sorted(self.__ds_drs_mapping):
                f.write('{directory},{drs_id}.{version}\n'.format(
                    directory=directory, drs_id=drs_id, version=version))

    def _write_json(self, drs):
        self.__file_drs.write(
            json.dumps(drs, sort_keys=True, indent=4, separators=(',', ': ')))

    def _get_term_uri(self, facet, term, ds=None):
        facet = facet.lower()
        term_l = self._convert_term(facet, term)
        if term_l in self.__facets.get_labels(facet).keys():
            return self.__facets.get_labels(facet)[term_l]
        elif term_l in self.__facets.get_alt_labels(facet).keys():
            return self.__facets.get_alt_labels(facet)[term_l]
        return None

    def _convert_term(self, facet, term):
        term = term.lower()
        if self.__use_mapping:
            return LocalVocabMappings.get_mapping(facet, term)
        return term

    def _open_files(self, ):
        if not self.__update_moles:
            self.__file_csv = open(MOLES_TAGS_FILE, 'w')
        self.__file_drs = open(ESGF_DRS_FILE, 'w')

    def _close_files(self, ):
        if not self.__update_moles:
            self.__file_csv.close()
        self.__file_drs.close()
