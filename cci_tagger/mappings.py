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

from cci_tagger.constants import ECV, FREQUENCY, INSTITUTION, PLATFORM,\
    SENSOR, PROCESSING_LEVEL, PRODUCT_VERSION


class LocalVocabMappings(object):
    """
    These mappings are used to map from values found in the files to the terms
    used in the vocab server.

    Not all of the net cdf files contain values that are in the vocabulary as
    some of them were created before the vocabulary was formalised. This class
    provides a means to map from terms found in the net cdf files to terms in
    the vocabulary. They are grouped into facets. The key of the dicts are the
    non compliant terms and the associated values are the correct terms to use.

    """

    __ecv = {
        'GHRSST': 'sea surface temperature',
    }

    __freq = {
        'daily': 'day',
        'P01D': 'day',
    }

    __freq_start_with = {
        'P1DT': 'day',
        'PT': 'day',
    }

    __institute = {
        'DTU Space - Div. of Geodynamics': 'DTU Space',
        'DTU Space - Div. of Geodynamics and NERSC': 'DTU Space',
        'DTU Space - Microwaves and Remote Sensing': 'DTU Space',
        'Deutsches Zentrum fuer Luft- und Raumfahrt (DLR)':
        'Deutsches Zentrum fuer Luft- und Raumfahrt',
        'ENVEO IT GmbH': 'ENVEO',
        'ESACCI': 'ESACCI_SST',
        'Plymouth Marine Laboratory Remote Sensing Group':
        'Plymouth Marine Laboratory',
        'Royal Netherlands Meteorological Institute (KNMI)':
        'Royal Netherlands Meteorological Institute',
        'SRON Netherlands Institute for Space Research':
        'Netherlands Institute for Space Research',
    }

    __level = {
        'level-3': 'l3',
    }

    __platform = {
        'ERS2': 'ERS-2',
        'ENV': 'ENVISAT',
        'EOS-AURA': 'AURA',
        'MetOpA': 'Metop-A',
        'Nimbus 7': 'Nimbus-7',
        'orbview-2/seastar': 'orbview-2',
        'SCISAT': 'SCISAT-1',
    }

    __sensor = {
        'AMSR-E': 'AMSRE',
        'ATSR2': 'ATSR-2',
        'AVHRR GAC': 'AVHRR',
        'AVHRR_GAC': 'AVHRR',
        'AVHRR_HRPT': 'AVHRR',
        'AVHRR_LAC': 'AVHRR',
        'AVHRR_MERGED': 'AVHRR',
        'GFO': 'GFO-RA',
        'MERIS_FRS': 'MERIS',
        'MERIS_RR': 'MERIS',
        'MODIS_MERGED': 'MODIS',
        'RA2': 'RA-2',
        'SMR_544.6GHz': 'SMR',
    }

    __version = {
        '03.02.': '03.02',
    }

    __merged_attr = {
        'AVHRR(NOAA-15,NOAA-16,NOAA-17,NOAA-18),MODIS(Aqua,Terra),AATSR(ENVISAT)':
            'NOAA-15,NOAA-16,NOAA-17,NOAA-18,Aqua,Terra,ENVISAT',
        'AVHRR(NOAA-15,NOAA-16,NOAA-17,NOAA-18)':
            'NOAA-15,NOAA-16,NOAA-17,NOAA-18',
        'MODIS(Aqua,Terra)': 'Aqua,Terra',
        'University of Leicester (UoL), UK': 'University of Leicester',
        'University of Leicester, UK': 'University of Leicester',
        'merged: ERS-2, ENVISAT, EOS-AURA, METOP-A':
            'ERS-2, ENVISAT, EOS-AURA, METOP-A',
        'merged: GOME, SCIAMACHY, OMI and GOME-2.':
            'GOME, SCIAMACHY, OMI, GOME-2',
        'MERISAATSR': 'MERIS,AATSR',
        'ICARE ; HYGEOS, Euratechnologies': 'ICARE , HYGEOS',
    }

    __mappings = {}
    __mappings[ECV] = __ecv
    __mappings[FREQUENCY] = __freq
    __mappings[INSTITUTION] = __institute
    __mappings[PROCESSING_LEVEL] = __level
    __mappings[PLATFORM] = __platform
    __mappings[SENSOR] = __sensor
    __mappings[PRODUCT_VERSION] = __version

    @classmethod
    def __str__(cls):
        """
        Get the string representation.

        @return the str representation of this class

        """
        output = ''
        for scheme in cls.__mappings.keys():
            scheme_dict = cls.__mappings[scheme]

            if len(scheme_dict) > 0:
                output = f'{output}\nMappings for {scheme}:\n'

                for key in scheme_dict:
                    output = f'{output}\tfrom\t {key}\n\tto\t {scheme_dict[key]}\n'

        if len(cls.__merged_attr) > 0:
            output = f'{output}\nMappings for merged attributes:\n'

            for key in cls.__merged_attr.keys():
                output = f'{output}\tfrom\t {key}\n\tto\t {cls.__merged_attr[key]}\n'

        return output

    @classmethod
    def get_mapping(cls, facet, term):
        """
        Get the mapping for the given facet and term.

        @param facet (str): the name of the facet
        @param term (str): the name of the term

        @return a str containing the mapped term or the original term if no
                mapping was found.


        """
        if facet not in cls.__mappings.keys():
            # no mapping for this facet
            return term

        term = term.lower()
        for key in cls.__mappings[facet].keys():
            if term == key.lower():
                return cls.__mappings[facet][key].lower()

        if facet == FREQUENCY:
            # extra stuff for frequency
            for key in cls.__freq_start_with.keys():
                if term.startswith(key.lower()):
                    return cls.__freq_start_with[key].lower()

        return term

    @classmethod
    def get_facet(cls):
        """
        Get the list of facets that mappings are available for.

        @return a list(str) the names of the known facets

        """
        return cls.__mappings.keys()

    @classmethod
    def split_attrib(cls, attr):
        """
        Split an attribute into its component bits.

        @param attr(str) the attribute to split

        @return a str containing the mapped term or the original term if no
                mapping was found.

        """
        if attr not in cls.__merged_attr.keys():
            # no mapping for this attr
            return attr
        return cls.__merged_attr[attr]


class UserVocabMappings(object):
    """
    These mappings are used to map from values found in the files to the terms
    used in the vocab server.

    Not all of the net cdf files contain values that are in the vocabulary as
    some of them were created before the vocabulary was formalised. This class
    provides a means to map from terms found in the net cdf files to terms in
    the vocabulary. They are grouped into facets. The key of the dicts are the
    non compliant terms and the associated values are the correct terms to use.

    """

    def __init__(self, mappings):
        """
        Initialise the class with a dictionary of mappings.
        """
        self.__mappings = mappings

    def __str__(self):
        """
        Get the string representation.

        @return the str representation of this class

        """
        output = ''

        for scheme in self.__mappings:
            scheme_dict = self.__mappings[scheme]

            if len(scheme_dict) > 0:
                output = f'{output}\nMappings for {scheme}:\n'

                for key in scheme_dict:
                    output = f'{output}\tfrom\t {key}\n\tto\t {scheme_dict[key]}\n'

        if len(self.__mappings['merged']) > 0:
            output = f'{output}\nMappings for merged attributes:\n'

            for key in self.__mappings['merged']:
                output = f'{output}\tfrom\t {key}\n\tto\t {self.__mappings["merged"][key]}\n'

        return output

    @property
    def has_merged_attr(self):
        return bool(self.__mappings.get('merged'))

    def get_mapping(self, facet, term):
        """
        Get the mapping for the given facet and term.

        @param facet (str): the name of the facet
        @param term (str): the name of the term

        @return a str containing the mapped term or the original term if no
                mapping was found.


        """
        # Check to see if there are any mappings for this facet
        facet_mappings = self.__mappings.get(facet)

        if not facet_mappings:
            # No mapping for this facet
            return term

        # Make sure that the term is lowercase
        term = term.lower()

        # Loop the possible mappings and match the lowercase term against the
        # lowercase key in the mapping
        for key in facet_mappings:
            if term == key.lower():
                return facet_mappings[key].lower()

        return term

    def get_facet(self):
        """
        Get the list of facets that mappings are available for.

        @return a list(str) the names of the known facets

        """
        return self.__mappings.keys()

    def split_attrib(self, attr):
        """
        In some cases, the attribute from the file is a merged list of many attributes.
        This method maps a complex string to a simpler comma separated string
        which can be used in the next steps of the code.

        @param attr(str) the attribute to split

        @return a str containing the mapped term or the original term if no
                mapping was found.

        """

        # Check if there is a merged attribute in the mapping.
        if self.has_merged_attr:
            mapped_val = self.__mappings['merged'].get(attr)

            # Return the mapped value, if there is one
            if mapped_val:
                return mapped_val

        # Defaults to just returning the input string
        return attr

