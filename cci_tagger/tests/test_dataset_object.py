# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '07 Feb 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from cci_tagger.dataset.dataset import Dataset
from cci_tagger.facets import Facets
from cci_tagger.dataset.dataset_tree import DatasetJSONMappings

# filepath = '/Users/vdn73631/Documents/dev/cci-tagger/cci_tagger/tests/ESACCI-SEASURFACESALINITY-L4-SSS-MERGED_OI_7DAY_RUNNINGMEAN_DAILY_25km-20120101-fv1.8.nc'
filepath = '/Users/vdn73631/Documents/dev/cci-tagger/cci_tagger/tests/ESACCI-SEAICE-L2P-SITHICK-SIRAL_CRYOSAT2-NH-20160101-fv2.0.nc'

facets = Facets()
json_mappings = DatasetJSONMappings('test_json_files')

dataset = json_mappings.get_dataset(filepath)

d = Dataset(dataset, json_mappings, facets)

# print(d.process_dataset(max_file_count=1))


uris = d.get_file_tags(filepath=filepath)
print(uris)

labels = d.get_drs_labels(uris)
print(labels)

drs = d.generate_ds_id(labels)
print(drs)