# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '05 Feb 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from .base import FileHandler
import netCDF4
from cci_tagger.constants import FREQUENCY, LEVEL_2_FREQUENCY, PRODUCT_VERSION, ALLOWED_GLOBAL_ATTRS

class NetcdfHandler(FileHandler):

    def __init__(self, filepath):

        self.nc_data = netCDF4.Dataset(filepath)

    @staticmethod
    def is_level2(proc_level):
        """
        Convenience method to determine whether we are dealing with a level 2 product
        :param proc_level: processing level string
        :return: bool
        """
        return bool(proc_level is not None and '2' in proc_level)

    def get_product_version(self):
        """
        Get the product version from the file.
        We do not have a vocab for the product version so just extract value
        :return: attribute (string) | None
        """

        try:
            attr = self.nc_data.getncattr(PRODUCT_VERSION)
        except AttributeError:
            return

        return attr

    def extract_facet_labels(self, proc_level):

        tags = {}

        for global_attr in ALLOWED_GLOBAL_ATTRS:

            # TODO: Implement logging with different verbosity
            if global_attr is FREQUENCY and self.is_level2(proc_level):
                tags[FREQUENCY] = [LEVEL_2_FREQUENCY]

            else:
                attr = self.nc_data.getncattr(global_attr)

                tags[global_attr] = attr

        # Add product version
        product_version = self.get_product_version()

        if product_version:
            tags[PRODUCT_VERSION] = product_version

        return tags






