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

from cci_tagger.constants import DATA_TYPE, FREQUENCY, INSTITUTION, PLATFORM, \
    SENSOR, ECV, PLATFORM_PROGRAMME, PLATFORM_GROUP, PROCESSING_LEVEL, \
    PRODUCT_STRING
from cci_tagger.settings import SPARQL_HOST_NAME
from cci_tagger.triple_store import TripleStore


class Facets(object):
    """
    This class is used to store data about the facets, that are obtained from
    the triple store.

    """
    # a dict of concept schemes
    __facets = None

    # mapping from platform uri to platform programme label
    __platform_programme_mappings = None

    # mapping from platform uri to platform group label
    __programme_group_mappings = None

    # mapping for process levels
    __proc_level_mappings = None

    def __init__(self, filepath=None):
        """
        Initialise the Facets class.

        """
        if filepath is not None:
            self._init_from_file(filepath)

        if self.__facets is None:
            self._init_facets()
        if self.__platform_programme_mappings is None:
            self._init_platform_mappings()
        if self.__proc_level_mappings is None:
            self._init_proc_level_mappings()

    def _init_facets(self):
        vocab_url = 'http://{}/scheme/cci'.format(SPARQL_HOST_NAME)
        self.__facets = {}
        self.__facets[DATA_TYPE] = TripleStore.get_concepts_in_scheme(
            '{}/dataType'.format(vocab_url))
        self.__facets[DATA_TYPE + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/dataType'.format(vocab_url)))
        self.__facets[ECV] = TripleStore.get_concepts_in_scheme(
            '{}/ecv'.format(vocab_url))
        self.__facets[ECV + '-alt'] = TripleStore.get_alt_concepts_in_scheme(
            '{}/ecv'.format(vocab_url))
        self.__facets[FREQUENCY] = (
            TripleStore.get_concepts_in_scheme(
                '{}/freq'.format(vocab_url)))
        self.__facets[FREQUENCY + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/freq'.format(vocab_url)))
        self.__facets[PLATFORM] = TripleStore.get_concepts_in_scheme(
            '{}/platform'.format(vocab_url))
        self.__facets[PLATFORM + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/platform'.format(vocab_url)))
        self.__facets[PLATFORM_PROGRAMME] = (
            TripleStore.get_concepts_in_scheme(
                '{}/platformProg'.format(vocab_url)))
        self.__facets[PLATFORM_PROGRAMME + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/platformProg'.format(vocab_url)))
        self.__facets[PLATFORM_GROUP] = TripleStore.get_concepts_in_scheme(
            '{}/platformGrp'.format(vocab_url))
        self.__facets[PLATFORM_GROUP + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/platformGrp'.format(vocab_url)))
        self.__facets[PROCESSING_LEVEL] = (
            TripleStore.get_concepts_in_scheme(
                '{}/procLev'.format(vocab_url)))
        self.__facets[PROCESSING_LEVEL + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/procLev'.format(vocab_url)))
        self.__facets[SENSOR] = TripleStore.get_concepts_in_scheme(
            '{}/sensor'.format(vocab_url))
        self.__facets[SENSOR].update(
            TripleStore.get_nerc_concepts_in_scheme(
                '{}/sensor'.format(vocab_url)))
        self.__facets[SENSOR + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/sensor'.format(vocab_url)))
        self.__facets[SENSOR + '-alt'].update(
            TripleStore.get_nerc_alt_concepts_in_scheme(
                '{}/sensor'.format(vocab_url)))
        self.__facets[INSTITUTION] = TripleStore.get_concepts_in_scheme(
            '{}/org'.format(vocab_url))
        self.__facets[INSTITUTION + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/org'.format(vocab_url)))
        self.__facets[PRODUCT_STRING] = TripleStore.get_concepts_in_scheme(
            '{}/product'.format(vocab_url))
        self.__facets[PRODUCT_STRING + '-alt'] = (
            TripleStore.get_alt_concepts_in_scheme(
                '{}/product'.format(vocab_url)))

    def _init_platform_mappings(self):
        """
        Initialise the platform-programme and programme-group mappings.

        Get the hierarchical mappings between programme, platform and group and
        store them locally.

        """
        self.__platform_programme_mappings = {}
        self.__programme_group_mappings = {}
        for platform in self.__facets[PLATFORM].values():
            program_label, program_uri = TripleStore.get_broader(platform)
            self.__platform_programme_mappings[platform] = program_label
            group_label, _ = TripleStore.get_broader(program_uri)
            if group_label:
                self.__programme_group_mappings[platform] = group_label

    def _init_proc_level_mappings(self):
        """
        Initialise the process level mappings.

        Get the hierarchical mappings between process levels and
        store them locally.

        """
        self.__proc_level_mappings = {}
        for proc_level in self.__facets[PROCESSING_LEVEL].values():
            _, proc_level_uri = TripleStore.get_broader(proc_level)
            if proc_level_uri != '':
                self.__proc_level_mappings[proc_level] = proc_level_uri

    def _init_from_file(self, path):
        import json

        with open(path) as input:
            data = json.load(input)

        self.__facets = data.get('_Facets__facets')
        self.__platform_programme_mappings = data.get('_Facets__platform_programme_mappings')
        self.__programme_group_mappings = data.get('_Facets__programme_group_mappings')
        self.__proc_level_mappings = data.get('_Facets__proc_level_mappings')

    def _serialize(self):

        return self.__dict__

    def export_mappings(self, path):
        """
        Export the facet, platform and proc_level_mappings to disk

        :param path: Output directory
        """
        import json

        with open(path, 'w') as output:
            json.dump(self._serialize(), output)

    def get_facet_names(self):
        """
        Get the list of facet names.

        @return  a list of str containing facet names

        """
        facet_names = []
        for key in self.__facets.keys():
            if not key.endswith('-alt'):
                facet_names.append(key)
        return facet_names

    def get_alt_labels(self, facet):
        """
        Get the facet alternative labels and uirs.

        @param facet (str): the name of the facet

        @return a dict where:\n
            key = lower case version of the concepts alternative label\n
            value = uri of the concept

        """
        return self.__facets['{}-alt'.format(facet)]

    def get_labels(self, facet):
        """
        Get the facet labels and uirs.

        @param facet (str): the name of the facet

        @return a dict where:\n
            key = lower case version of the concepts preferred label\n
            value = uri of the concept

        """
        return self.__facets[facet]

    def get_platforms_programme(self, uri):
        """"
        Get the programme label for the given platform URI.

        @param uri (str): the URI of the platform

        @return a str containing the label of the programme that contains the
                platform

        """
        return self.__platform_programme_mappings[uri]

    def get_programme_labels(self):
        """
        Get a list of the programme labels, where a programme is a container
        for platforms.

        @return a list of str containing programme labels

        """
        return self.__platform_programme_mappings.values()

    def get_programmes_group(self, uri):
        """"
        Get the group label for the given programme URI.

        @param uri (str): the URI of the programme

        @return a str containing the label of the group that contains the
                programme

        """
        return self.__programme_group_mappings[uri]

    def get_group_labels(self):
        """
        Get a list of the group labels, where a group is a container
        for programmes.

        @return a list of str containing group labels

        """
        return self.__programme_group_mappings.values()

    def get_broader_proc_level(self, uri):
        """"
        Get the broader process level URI for the given process level URI.

        @param uri (str): the URI of the process level

        @return a str containing the label of the process level

        """
        return self.__proc_level_mappings.get(uri)

